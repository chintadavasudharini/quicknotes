import secrets

def otp_gen():
    otp=""
    u_l=[chr(i) for i in range(ord('A'),ord('Z')+1)]
    s_l=[chr(i) for i in range(ord('a'),ord('z')+1)]
    for _ in range(2):
        otp=otp+secrets.choice(u_l)
        otp=otp+secrets.choice(s_l)
        otp=otp+str(secrets.randbelow(10))
    return otp