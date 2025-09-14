from constructs import Construct
from aws_cdk import (
    Stack, Duration, RemovalPolicy,
    aws_s3 as s3, aws_dynamodb as ddb,
    aws_lambda as _lambda, aws_apigateway as apigw,
    aws_cognito as cognito,
    aws_iam as iam,
    aws_iam as iam,
    Environment,
    Stack,
    aws_dynamodb as dynamodb
)

class BackendStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.user_pool = cognito.UserPool(
            self, "MyNewUserPool",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(email=True, username=True),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True
            ),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=True)
            ),
            custom_attributes={
                "firstName": cognito.StringAttribute(min_len=1, max_len=50),
                "lastName": cognito.StringAttribute(min_len=1, max_len=50),
                "birthDate": cognito.StringAttribute(min_len=10, max_len=10),
                "role": cognito.StringAttribute(min_len=1, max_len=20),
            },
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            removal_policy=RemovalPolicy.DESTROY
        )

        # topic = sns.Topic(
        #     self, "BackendTopic"
        # )

        # topic.add_subscription(subs.SqsSubscription(queue))
        audio = s3.Bucket(self,"Audio",removal_policy=RemovalPolicy.DESTROY,auto_delete_objects=True)
        images = s3.Bucket(self,"Images",removal_policy=RemovalPolicy.DESTROY,auto_delete_objects=True)
    
        table = ddb.Table(self,"MusicTable",
            partition_key=ddb.Attribute(name="PK", type=ddb.AttributeType.STRING),
            table_name='content',
            sort_key=ddb.Attribute(name="SK", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY)

        get_url = _lambda.Function(self,"GetUploadUrl",
            runtime=_lambda.Runtime.PYTHON_3_11, handler="get_upload_url.handler",
            function_name="GetUploadUrl",
            code=_lambda.Code.from_asset("backend/post-content"), timeout=Duration.seconds(10),
            environment={"AUDIO_BUCKET":audio.bucket_name,"IMAGES_BUCKET":images.bucket_name})
        audio.grant_put(get_url); images.grant_put(get_url)

        create_single = _lambda.Function(self,"CreateSingle",
            runtime=_lambda.Runtime.PYTHON_3_11, handler="create_single.handler",
            function_name="CreateSingle",
            code=_lambda.Code.from_asset("backend/post-content"), timeout=Duration.seconds(10),
            environment={"TABLE":table.table_name})
        create_album  = _lambda.Function(self,"CreateAlbum",
            function_name="CreateAlbum",
            runtime=_lambda.Runtime.PYTHON_3_11, handler="create_album.handler",
            code=_lambda.Code.from_asset("backend/post-content"), timeout=Duration.seconds(10),
            environment={"TABLE":table.table_name})
        table.grant_write_data(create_single); table.grant_write_data(create_album)
        
        # API Gateway
        api = apigw.RestApi(self, "MyApi")

        # Cognito Authorizer
        authorizer = apigw.CognitoUserPoolsAuthorizer(
            self, "MyAPIAuthorizer",
            cognito_user_pools=[self.user_pool]
        )

        api.root.add_resource("upload-url").add_method("POST", apigw.LambdaIntegration(get_url), authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer)
        contents = api.root.add_resource("contents")
        contents.add_resource("single").add_method("POST", apigw.LambdaIntegration(create_single), authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer)
        contents.add_resource("album").add_method("POST", apigw.LambdaIntegration(create_album), authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer)
       
        contentTable = dynamodb.Table(
            self, "content",
            partition_key=dynamodb.Attribute(name="contentType", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="contentName", type=dynamodb.AttributeType.STRING),
            table_name="content",
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
        )

        genresTable = dynamodb.Table(
            self, "genres",
            partition_key=dynamodb.Attribute(name="genreName", type=dynamodb.AttributeType.STRING),
            table_name="genres",
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
        )

        # 2. User Pool Client
        user_pool_client = cognito.UserPoolClient(
            self, "NewUserPoolClient",
            user_pool=self.user_pool
        )

        pre_signup_lambda = _lambda.Function(
            self, "PreSignUpLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="pre_signup.handler",
            code=_lambda.Code.from_asset("backend/lambdas/auth")
        )

        pre_signup_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["cognito-idp:AdminGetUser", "cognito-idp:ListUsers"],
                resources=[f"arn:aws:cognito-idp:{self.region}:{self.account}:userpool/*"]
            )
        )

        self.user_pool.add_trigger(
            cognito.UserPoolOperation.PRE_SIGN_UP,
            pre_signup_lambda
        )

        items = api.root.add_resource("items")

        items.add_method(
            "GET",
            apigw.MockIntegration(),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer
        )
