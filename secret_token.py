from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from secretkeys import secret_key, salt

def endata(data):
    serializer = URLSafeTimedSerializer(secret_key)
    return serializer.dumps(data, salt=salt)

def dndata(token, max_age=None):   
    serializer = URLSafeTimedSerializer(secret_key)
    try:
        return serializer.loads(token, salt=salt, max_age=max_age)  
    except SignatureExpired:
        print("OTP expired")
        return None
    except BadSignature:
        print("Invalid OTP")
        return None
