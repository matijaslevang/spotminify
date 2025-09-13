import boto3

cognito = boto3.client("cognito-idp")

def handler(event, context):
    email = event["request"]["userAttributes"].get("email")

    try:
        # Try to find user by email
        response = cognito.admin_get_user(
            UserPoolId=event["userPoolId"],
            Username=email
        )
        # If it doesn't fail, it means it found a user with the same email - bad
        raise Exception("User with this email already exists.")

    except cognito.exceptions.UserNotFoundException:
        # If it fails, it means the email is unique in the system - good
        pass

    # Auto confirm & verify
    event['response']['autoConfirmUser'] = True
    event['response']['autoVerifyEmail'] = True

    # Adding default role
    if "custom:role" not in event["request"]["userAttributes"]:
        event["request"]["userAttributes"]["custom:role"] = "User"

    return event
