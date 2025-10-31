import os
from huggingface_hub import InferenceClient

# Use a small, freely-usable instruct model
# You can swap to any chat-completion capable model you prefer on HF Inference.
DEFAULT_MODEL = os.getenv("HF_MODEL", "HuggingFaceH4/zephyr-7b-beta")

_client = None
def _client_lazy():
    global _client
    if _client is None:
        tok = os.getenv("HF_TOKEN", "")
        if not tok:
            return None
        _client = InferenceClient(api_key=tok)
    return _client

def has_hf_token() -> bool:
    return bool(os.getenv("HF_TOKEN", ""))

def hf_finance_chatbot(user_message: str) -> str:
    client = _client_lazy()
    if client is None:
        return mini_chatbot_fallback(user_message)

    try:
        resp = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content":
                 "You are FinGenie, a concise, practical personal-finance assistant for students & young adults. "
                 "Be clear, specific, and avoid investment advice that requires licenses. "
                 "If the user uploaded a statement, base suggestions on typical reading of bank transactions."},
                {"role": "user", "content": user_message},
            ],
            max_tokens=512,
            temperature=0.4,
        )
        msg = resp.choices[0].message.get("content", "").strip()
        return msg or "I couldn't generate a response right now."
    except Exception as e:
        return f"(HF fallback) {mini_chatbot_fallback(user_message)}"

# Lightweight local fallback if HF token is missing
def mini_chatbot_fallback(message: str) -> str:
    msg = (message or "").lower()
    if "budget" in msg or "save" in msg:
        return "Try 50/30/20: 50% needs, 30% wants, 20% savings. Automate savings on salary day."
    if "credit" in msg:
        return "Pay full before due date, keep utilization <30%, avoid cash advances."
    if "emergency" in msg:
        return "Build an emergency fund for 3–6 months of expenses in a liquid account."
    if "invest" in msg or "sip" in msg:
        return "Start with a simple index/balanced fund SIP after building emergency buffer and clearing high-interest debt."
    return "Ask me about budgeting, credit-cards, EMIs, emergency funds, or reading your statement."
