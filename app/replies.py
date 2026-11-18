"""Fixed replies: the answers we send when a layer stops a message. No AI, no cost.

Every reply is in English and Bangla together, because Layer 3 happens before we know anything else about the person.
"""
from app.schemas import Reply


def fixed_reply(reason: str, max_chars: int) -> Reply:
    if reason == "too_long":
        return Reply(
            status="refused",
            reply=f"Your message is too long. Please keep it under {max_chars} characters.\n"
                  f"আপনার বার্তাটি অনেক বড়। অনুগ্রহ করে {max_chars} অক্ষরের মধ্যে লিখুন।",
        )
    if reason == "rate":
        return Reply(
            status="refused",
            reply="You are sending messages too fast. Please wait a minute and try again.\n"
                  "আপনি খুব দ্রুত বার্তা পাঠাচ্ছেন। অনুগ্রহ করে এক মিনিট পরে আবার চেষ্টা করুন।",
        )
    if reason == "user_daily":
        return Reply(
            status="refused",
            reply="You have reached today's message limit. Please try again tomorrow.\n"
                  "আজকের বার্তার সীমা শেষ হয়েছে। অনুগ্রহ করে আগামীকাল আবার চেষ্টা করুন।",
        )
    if reason == "global_daily":
        return Reply(
            status="needs_human",
            reply="We are very busy right now. A team member will reply to you soon.\n"
                  "আমরা এখন খুব ব্যস্ত। আমাদের একজন সদস্য শীঘ্রই আপনাকে উত্তর দেবেন।",
        )
    raise ValueError(f"unknown reason: {reason}")