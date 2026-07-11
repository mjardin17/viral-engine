def verify_account_email(creds):
    print("\n[STEP] Verifying signed-in account email...")
    try:
        from googleapiclient.discovery import build as build_oauth
        oauth2 = build_oauth("oauth2", "v2", credentials=creds)
        info = oauth2.userinfo().get().execute()
        email = info.get("email", "UNKNOWN")
        print(f"  Signed-in account email: {email}")

        if email.lower() != "godsandgloryai@gmail.com":
            print("\n" + "!" * 60)
            print("  MISMATCH: This token is NOT for godsandgloryai@gmail.com")
            print(f"  It is signed in as: {email}")
            print("  This is likely the OLD duplicate channel with the wrong email.")
            print("  Delete token_gg.pickle and rerun, then pick the correct")
            print("  account in the browser login screen.")
            print("!" * 60)
            return False
        else:
            print("[OK] Confirmed: signed in as godsandgloryai@gmail.com")
            return True
    except Exception as e:
        print(f"[WARN] Could not verify account email: {e}")
        print("Add 'https://www.googleapis.com/auth/userinfo.email' to SCOPES if this keeps failing.")
        return None