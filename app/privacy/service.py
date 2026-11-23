from app.models import PrivacyCheck, now
from app.privacy import assess


def check_post(db, post):
    existing = db.get(PrivacyCheck, post.post_id)
    from app.privacy import VERSION
    if existing and existing.input_hash == post.text_hash and existing.method_version == VERSION and existing.reviewed_at:
        return existing
    title = assess(post.title or '')
    result = assess((post.title or '') + '\n' + post.text)
    check = PrivacyCheck(post_id=post.post_id, input_hash=post.text_hash,
        safe_title=title.safe_text, safe_text=result.safe_text,
        findings=result.findings, risk=result.risk, status=result.status,
        method_version=result.method_version, checked_at=now())
    db.merge(check)
    return check
