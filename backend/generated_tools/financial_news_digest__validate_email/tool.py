import re

def validate_email(email_address):
    try:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(pattern, email_address):
            return {'status': 'valid', 'email': email_address}
        return {'status': 'invalid', 'email': email_address, 'error': 'Invalid format'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
