from constructs import Construct
from aws_cdk import (
    RemovalPolicy,
    Stack,
    aws_apigateway as apigw,
    aws_cognito as cognito,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_sqs as sqs,
    Stack,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_lambda_event_sources as lambda_event_sources
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

        table_genre_subscriptions = dynamodb.Table(
            self, "GenreSubscriptions",
            partition_key=dynamodb.Attribute(name="username", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="genreName", type=dynamodb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY,
            global_secondary_indexes=[
                dynamodb.GlobalSecondaryIndex(
                    index_name="ByGenreName",
                    partition_key=dynamodb.Attribute(name="genreName", type=dynamodb.AttributeType.STRING),
                    sort_key=dynamodb.Attribute(name="username", type=dynamodb.AttributeType.STRING),
                    projection_type=dynamodb.ProjectionType.ALL,
                )
            ]
        )

        table_artist_subscriptions = dynamodb.Table(
            self, "ArtistSubscriptions",
            partition_key=dynamodb.Attribute(name="username", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="artistId", type=dynamodb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY,
            global_secondary_indexes=[
                dynamodb.GlobalSecondaryIndex(
                    index_name="ByArtistId",
                    partition_key=dynamodb.Attribute(name="artistId", type=dynamodb.AttributeType.STRING),
                    sort_key=dynamodb.Attribute(name="username", type=dynamodb.AttributeType.STRING),
                    projection_type=dynamodb.ProjectionType.ALL,
                )
            ]
        )

        table_activity = dynamodb.Table(
            self, "Activity",
            partition_key=dynamodb.Attribute(name="username", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="accessTime", type=dynamodb.AttributeType.STRING),  # store datetime as ISO string
            removal_policy=RemovalPolicy.DESTROY
        )

        table_ratings = dynamodb.Table(
            self, "Ratings",
            partition_key=dynamodb.Attribute(name="username", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="contentId", type=dynamodb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY
        )

        table_score_cache = dynamodb.Table(
            self, "ScoreCache",
            partition_key=dynamodb.Attribute(name="username", type=dynamodb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY
        )

        table_feed_cache = dynamodb.Table(
            self, "FeedCache",
            partition_key=dynamodb.Attribute(name="username", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="contentId", type=dynamodb.AttributeType.STRING),
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


        # API Gateway
        api = apigw.RestApi(self, "MyApi")

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

        feed = api.root.add_resource("feed")

        get_feed_lambda = _lambda.Function(
            self, "GetFeedLambda",
            function_name="GetFeedLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="get_feed.handler",
            code=_lambda.Code.from_asset("backend/lambdas/feed"),
            environment={
                "FEED_TABLE_NAME" : table_feed_cache.table_name
            }
        )

        feed.add_method(
            "GET",
            apigw.LambdaIntegration(get_feed_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer
        )

        table_feed_cache.grant_read_data(get_feed_lambda)

        update_feed_added_content_lambda = _lambda.Function(
            self, "UpdateFeedAddedContentLambda",
            function_name="UpdateFeedAddedContentLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="update_feed_added_content.handler",
            code=_lambda.Code.from_asset("backend/lambdas/feed"),
            environment={
                "USER_POOL_ID": self.user_pool.user_pool_id,
                "SCORE_TABLE_NAME" : table_score_cache.table_name,
                "FEED_TABLE_NAME" : table_feed_cache.table_name
            }
        )

        table_score_cache.grant_read_data(update_feed_added_content_lambda)
        table_feed_cache.grant_read_write_data(update_feed_added_content_lambda)

        update_feed_added_content_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["cognito-idp:ListUsers"],
                resources=[f"arn:aws:cognito-idp:{self.region}:{self.account}:userpool/{self.user_pool.user_pool_id}"]
            )
        )

        update_feed_score_specific_user_lambda = _lambda.Function(
            self, "UpdateFeedScoreSpecificUserLambda",
            function_name="UpdateFeedScoreSpecificUserLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="update_feed_score_specific_user.handler",
            code=_lambda.Code.from_asset("backend/lambdas/feed"),
            environment={
                "SCORE_TABLE_NAME" : table_score_cache.table_name
            }
        )

        table_score_cache.grant_read_write_data(update_feed_score_specific_user_lambda)

        update_feed_specific_user_lambda = _lambda.Function(
            self, "UpdateFeedSpecificUserLambda",
            function_name="UpdateFeedSpecificUserLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="update_feed_specific_user.handler",
            code=_lambda.Code.from_asset("backend/lambdas/feed"),
            environment={
                "SCORE_TABLE_NAME" : table_score_cache.table_name,
                "FEED_TABLE_NAME" : table_feed_cache.table_name
            }
        )

        table_score_cache.grant_read_data(update_feed_specific_user_lambda)
        table_feed_cache.grant_read_write_data(update_feed_specific_user_lambda)

        
        
        # ----------------- SQS -----------------

        update_feed_added_content_queue = sqs.Queue(
            self, "UpdateFeedAddedContentQueue",
            queue_name="update-feed-added-content-queue",
            removal_policy=RemovalPolicy.DESTROY
        )

        update_feed_score_specific_user_queue = sqs.Queue(
            self, "UpdateFeedScoreSpecificUserQueue",
            queue_name="update-feed-score-specific-user-queue",
            removal_policy=RemovalPolicy.DESTROY
        )

        update_feed_specific_user_queue = sqs.Queue(
            self, "UpdateFeedSpecificUserQueue",
            queue_name="update-feed-specific-user-queue",
            removal_policy=RemovalPolicy.DESTROY
        )
        
        update_feed_added_content_queue.grant_consume_messages(update_feed_added_content_lambda)

        update_feed_added_content_lambda.add_event_source(
            lambda_event_sources.SqsEventSource(update_feed_added_content_queue)
        )

        update_feed_score_specific_user_queue.grant_consume_messages(update_feed_score_specific_user_lambda)

        update_feed_score_specific_user_lambda.add_event_source(
            lambda_event_sources.SqsEventSource(update_feed_score_specific_user_queue)
        )

        update_feed_specific_user_queue.grant_consume_messages(update_feed_specific_user_lambda)

        update_feed_specific_user_lambda.add_event_source(
            lambda_event_sources.SqsEventSource(update_feed_specific_user_queue)
        )
