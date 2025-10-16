from constructs import Construct
from aws_cdk import (
    RemovalPolicy,
    Stack,
    aws_apigateway as apigw,
    aws_cognito as cognito,
    aws_lambda as _lambda,
    aws_iam as iam,
    Stack,
    aws_dynamodb as dynamodb,
    aws_s3 as s3
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

        contentTable = dynamodb.Table.from_table_name(
            self, "content-imported",
            "content"
        )

        genresTable = dynamodb.Table.from_table_name(
            self, "genres-imported",
            "genres"
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

        artist_bucket = s3.Bucket(
            self, "ArtistImagesBucket",
            bucket_name=f"artist-images-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL
        )

        create_artist_lambda = _lambda.Function(
            self, "CreateArtistLambda",
            function_name="CreateArtistLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="create_artist.handler",
            code=_lambda.Code.from_asset("backend/lambdas/content"),
            environment={
                "BUCKET_NAME": artist_bucket.bucket_name,
                "TABLE_NAME": contentTable.table_name
            }
        )

        artist_bucket.grant_put(create_artist_lambda)
        contentTable.grant_write_data(create_artist_lambda)

        # album
        create_album_lambda = _lambda.Function(
            self, "CreateAlbumLambda",
            function_name="CreateAlbumLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="create_album.handler",
            code=_lambda.Code.from_asset("backend/post-content"),
            environment={
                "BUCKET_NAME": artist_bucket.bucket_name,
                "TABLE_NAME": contentTable.table_name
            }
        )
        # single
        create_single_lambda = _lambda.Function(
            self, "CreateSingleLambda",
            function_name="CreateSingleLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="create_single.handler",
            code=_lambda.Code.from_asset("backend/post-content"),
            environment={
                "BUCKET_NAME": artist_bucket.bucket_name,
                "TABLE_NAME": contentTable.table_name
            }
        )
        artist_bucket.grant_put(create_single_lambda); 
        artist_bucket.grant_put(create_album_lambda)
        contentTable.grant_write_data(create_single_lambda); 
        contentTable.grant_write_data(create_album_lambda)

        # API Gateway
        #api = apigw.RestApi(self, "MyApi")
        api = apigw.RestApi(
            self, "MyApi",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,  # ili ["POST","OPTIONS"]
                allow_headers=[
                    "Content-Type",
                    "Authorization",
                    "X-Amz-Date",
                    "X-Api-Key",
                    "X-Amz-Security-Token"
                ],
            ),
        )
        
        api.add_gateway_response(
        "Default4xx",
        type=apigw.ResponseType.DEFAULT_4_XX,  # <-- ovde
        response_headers={
            "Access-Control-Allow-Origin": "'*'",
            "Access-Control-Allow-Headers": "'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token'",
            "Access-Control-Allow-Methods": "'OPTIONS,GET,PUT,POST,DELETE'",
        },
        )

        api.add_gateway_response(
            "Default5xx",
            type=apigw.ResponseType.DEFAULT_5_XX,  # <-- i ovde
            response_headers={
                "Access-Control-Allow-Origin": "'*'",
                "Access-Control-Allow-Headers": "'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token'",
                "Access-Control-Allow-Methods": "'OPTIONS,GET,PUT,POST,DELETE'",
            },
        )



        # apigw.Cors.add_cors_options(
        #     singles,
        #     allow_origins=apigw.Cors.ALL_ORIGINS,
        #     allow_methods=["POST","OPTIONS"],
        #     allow_headers=["Content-Type","Authorization","X-Amz-Date","X-Api-Key","X-Amz-Security-Token"],
        # )
        # apigw.Cors.add_cors_options(
        #     albums,
        #     allow_origins=apigw.Cors.ALL_ORIGINS,
        #     allow_methods=["POST","OPTIONS"],
        #     allow_headers=["Content-Type","Authorization","X-Amz-Date","X-Api-Key","X-Amz-Security-Token"],
        # )

        # Cognito Authorizer
        authorizer = apigw.CognitoUserPoolsAuthorizer(
            self, "MyAPIAuthorizer",
            cognito_user_pools=[self.user_pool]
        )

        items = api.root.add_resource("items")

        items.add_method(
            "GET",
            apigw.MockIntegration(),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer
        )

        artists = api.root.add_resource("artists")

        artists.add_method(
            "POST",
            apigw.LambdaIntegration(create_artist_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer
        )
        
        albums = api.root.add_resource("albums")

        albums.add_method(
            "POST",
            apigw.LambdaIntegration(create_album_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer
        )
        
        
        singles = api.root.add_resource("singles")

        singles.add_method(
            "POST",
            apigw.LambdaIntegration(create_single_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer
        )
        
        audio_bucket = s3.Bucket(
            self, "SongFilesBucket",
            bucket_name=f"audio-files-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL
        )
        
        images_bucket = s3.Bucket(
            self, "SongImagesBucket",
            bucket_name=f"song-images-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL
        )
        
        get_url = _lambda.Function(
            self,"GetUploadUrl",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="get_upload_url.handler",
            code=_lambda.Code.from_asset("backend/post-content"),
            environment={"AUDIO_BUCKET":audio_bucket.bucket_name,"IMAGES_BUCKET": images_bucket.bucket_name},
        )
        audio_bucket.grant_put(get_url); 
        images_bucket.grant_put(get_url)

        r_upload = api.root.add_resource("upload-url")
        r_upload.add_method("POST", apigw.LambdaIntegration(get_url),
            authorization_type=apigw.AuthorizationType.COGNITO, authorizer=authorizer)

