"""AI-powered conflict analysis using IBM watsonx.ai or mock backend."""

import json
import os
import time
from typing import Literal

import requests

from git.parser import ConflictHunk


# Prompt template for AI analysis
ANALYSIS_PROMPT = """You are a merge conflict analyst. Given the following conflict hunk, respond ONLY with
valid JSON in this exact format with no preamble or markdown:
{{"summary": "<one sentence: why does this conflict exist>",
 "suggestion": "<one to three sentences: how to resolve it>"}}

File: {file}
Conflict type: {kind}

=== OURS ({ours_branch}) ===
{ours_text}

=== BASE (common ancestor) ===
{base_text}

=== THEIRS ({theirs_branch}) ===
{theirs_text}"""


def _get_iam_token(api_key: str) -> str:
    """
    Exchange IBM Cloud API key for an IAM access token.
    
    Args:
        api_key: IBM Cloud API key from WATSONX_API_KEY env var
        
    Returns:
        IAM access token string
        
    Raises:
        requests.RequestException: If token exchange fails
    """
    url = "https://iam.cloud.ibm.com/identity/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
        "apikey": api_key
    }
    
    response = requests.post(url, headers=headers, data=data, timeout=10)
    response.raise_for_status()
    
    return response.json()["access_token"]


def _call_watsonx(prompt: str, api_key: str) -> dict:
    """
    Call IBM watsonx.ai text generation API.
    
    Args:
        prompt: Formatted analysis prompt
        api_key: IBM Cloud API key
        
    Returns:
        dict with 'summary' and 'suggestion' keys
        
    Raises:
        requests.RequestException: If API call fails
        json.JSONDecodeError: If response is not valid JSON
    """
    # Get IAM token
    token = _get_iam_token(api_key)
    
    # Call watsonx.ai chat API
    url = "https://us-south.ml.cloud.ibm.com/ml/v1/text/chat?version=2023-05-29"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "model_id": "meta-llama/llama-3-3-70b-instruct",
        "project_id": os.getenv("WATSONX_PROJECT_ID", ""),
        "max_tokens": 300,
        "temperature": 0.1,
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    
    # Extract generated text from chat response
    result = response.json()
    generated_text = result["choices"][0]["message"]["content"].strip()
    
    # Parse JSON response
    # Handle potential markdown code blocks
    if generated_text.startswith("```"):
        # Remove markdown code block markers
        lines = generated_text.split("\n")
        generated_text = "\n".join(lines[1:-1]) if len(lines) > 2 else generated_text
    
    return json.loads(generated_text)


def _call_mock() -> dict:
    """
    Return mock AI analysis for testing without API calls.
    
    Returns:
        dict with 'summary' and 'suggestion' keys
    """
    return {
        "summary": "Both branches modified the same function in incompatible ways.",
        "suggestion": "Review both implementations and manually merge the logic, preserving both changes where possible."
    }


def analyse_hunk(
    hunk: ConflictHunk,
    ours_branch: str,
    theirs_branch: str
) -> ConflictHunk:
    """
    Analyse a conflict hunk using AI and populate ai_summary and ai_suggestion.
    
    The backend is selected via the AI_BACKEND environment variable:
    - "watsonx" — calls IBM watsonx.ai (requires WATSONX_API_KEY env var)
    - "mock" — returns deterministic fake responses (default)
    
    Args:
        hunk: ConflictHunk to analyse
        ours_branch: Name of the current branch (HEAD)
        theirs_branch: Name of the incoming branch
        
    Returns:
        The same ConflictHunk with ai_summary and ai_suggestion populated.
        On error, sets ai_summary to "Analysis unavailable" and ai_suggestion to "".
    """
    backend = os.getenv("AI_BACKEND", "mock").lower()
    
    try:
        # Format the prompt
        ours_text = "".join(hunk.ours) if hunk.ours else "(empty)"
        base_text = "".join(hunk.base) if hunk.base else "(empty)"
        theirs_text = "".join(hunk.theirs) if hunk.theirs else "(empty)"
        
        prompt = ANALYSIS_PROMPT.format(
            file=hunk.file,
            kind=hunk.kind,
            ours_branch=ours_branch,
            ours_text=ours_text,
            base_text=base_text,
            theirs_branch=theirs_branch,
            theirs_text=theirs_text
        )
        
        # Call the appropriate backend
        if backend == "watsonx":
            api_key = os.getenv("WATSONX_API_KEY")
            if not api_key:
                raise ValueError("WATSONX_API_KEY environment variable not set")
            result = _call_watsonx(prompt, api_key)
        else:
            # Default to mock
            result = _call_mock()
        
        # Populate the hunk
        hunk.ai_summary = result.get("summary", "")
        hunk.ai_suggestion = result.get("suggestion", "")
        
    except Exception as e:
        # Never raise — gracefully degrade
        hunk.ai_summary = "Analysis unavailable"
        hunk.ai_suggestion = ""
        # Log error for debugging (in production, use proper logging)
        print(f"AI analysis error for {hunk.file} hunk {hunk.hunk_index}: {e}")
    
    return hunk


def analyse_all(
    hunks: list[ConflictHunk],
    ours_branch: str,
    theirs_branch: str
) -> None:
    """
    Analyse all conflict hunks using AI.
    
    For the watsonx backend, adds a 0.5s delay between calls to avoid rate limiting.
    Modifies hunks in place.
    
    Args:
        hunks: List of ConflictHunks to analyse
        ours_branch: Name of the current branch (HEAD)
        theirs_branch: Name of the incoming branch
    """
    backend = os.getenv("AI_BACKEND", "mock").lower()
    
    for i, hunk in enumerate(hunks):
        analyse_hunk(hunk, ours_branch, theirs_branch)
        
        # Rate limiting for watsonx
        if backend == "watsonx" and i < len(hunks) - 1:
            time.sleep(0.5)


# Made with Bob
