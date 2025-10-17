from constructs import Construct
from aws_cdk import (
    RemovalPolicy,
    Stack,
    aws_apigateway as apigw,
    aws_cognito as cognito,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_sqs as sqs,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_lambda_event_sources as lambda_event_sources,
    custom_resources as cr,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subscriptions,
    aws_logs as logs
)

import uuid

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

        table_subscriptions = dynamodb.Table(
            self, "Subscriptions",
            partition_key=dynamodb.Attribute(name="username", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="targetId", type=dynamodb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY
        )

        table_subscriptions.add_global_secondary_index(
            index_name="by-target-id",
            partition_key=dynamodb.Attribute(name="targetId", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="username", type=dynamodb.AttributeType.STRING)
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

        table_artists = dynamodb.Table(
            self, "Artists",
            partition_key=dynamodb.Attribute(name="artistId", type=dynamodb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY
        )

        # contentTable = dynamodb.Table.from_table_name(
        #     self, "content-imported",
        #     "content"
        # )

        table_genres = dynamodb.Table(
            self, "Genres",
            partition_key=dynamodb.Attribute(name="genreId", type=dynamodb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY
        )

        table_albums = dynamodb.Table(
            self, "Albums",
            partition_key=dynamodb.Attribute(name="albumId", type=dynamodb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY
        )
        
        table_singles = dynamodb.Table(
            self, "Singles",
            partition_key=dynamodb.Attribute(name="singleId", type=dynamodb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY
        )
        
        initial_genres = [
            'Pop', 'Rock', 'Jazz', 'Hip-Hop', 'Classical', 'Electronic', 'Lo-Fi', 'R&B', 'Metal'
        ]

        genre_items = [
            {
                'PutRequest': {
                    'Item': {
                        'genreId': {'S': str(uuid.uuid4())},
                        'genreName': {'S': genre}}
                }
            } for genre in initial_genres
        ]

        genre_seeder = cr.AwsCustomResource(
            self, "GenresSeeder",
            on_create=cr.AwsSdkCall(
                service="DynamoDB",
                action="batchWriteItem",
                parameters={
                    "RequestItems": {
                        table_genres.table_name: genre_items
                    }
                },
                physical_resource_id=cr.PhysicalResourceId.of("GenresSeederResourceId")
            ),
            policy=cr.AwsCustomResourcePolicy.from_statements([
                iam.PolicyStatement(
                    actions=["dynamodb:BatchWriteItem"],
                    resources=[table_genres.table_arn]
                )
            ])
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
                "TABLE_NAME": table_artists.table_name
            }
        )

        get_genres_lambda = _lambda.Function(
            self, "GetGenresLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="get_genres.handler",
            code=_lambda.Code.from_asset("backend/lambdas/content"),
            environment={
                "TABLE_NAME": table_genres.table_name
            }
        )

        table_genres.grant_read_data(get_genres_lambda)
        artist_bucket.grant_put(create_artist_lambda)
        table_artists.grant_write_data(create_artist_lambda)


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

        genres_resource = api.root.add_resource(
            "genres",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=["GET", "OPTIONS"],
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
            )
        )
        genres_resource.add_method(
            "GET",
            apigw.LambdaIntegration(get_genres_lambda)
        )

        artists = api.root.add_resource("artists",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=["GET", "POST", "OPTIONS"],
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
            ))

        artists.add_method(
            "POST",
            apigw.LambdaIntegration(create_artist_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer
        )
        
        albums = api.root.add_resource("albums",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=["GET", "POST","PUT", "OPTIONS"],
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
            ))

        singles = api.root.add_resource("singles",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=["GET", "POST", "PUT", "OPTIONS"],
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
            ))
        
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
        
        audio_bucket.add_cors_rule(
            allowed_methods=[s3.HttpMethods.PUT, s3.HttpMethods.GET, s3.HttpMethods.HEAD],
            allowed_origins=["http://localhost:4200"],   # or "*" for quick dev
            allowed_headers=["*"],
            exposed_headers=["ETag"],
            max_age=3000,
        )
        images_bucket.add_cors_rule(
            allowed_methods=[s3.HttpMethods.PUT, s3.HttpMethods.GET, s3.HttpMethods.HEAD],
            allowed_origins=["http://localhost:4200"],   # or "*"
            allowed_headers=["*"],
            exposed_headers=["ETag"],
            max_age=3000,
        )
        # NEW create_album_lambda
        create_album_lambda = _lambda.Function(
            self, "CreateAlbumLambda",
            function_name="CreateAlbumLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="create_album.handler",
            code=_lambda.Code.from_asset("backend/post-content"),
            environment={
                "ALBUMS_TABLE":  table_albums.table_name, # umesto albums.table_name
                "SINGLES_TABLE": table_singles.table_name,  # umesto singles.table_name
                "AUDIO_BUCKET":  audio_bucket.bucket_name,
                "IMAGES_BUCKET": images_bucket.bucket_name,
            },
            #log_retention=logs.RetentionDays.ONE_WEEK
        )

        # NEW create_single_lambda
        
        create_single_lambda = _lambda.Function(
            self, "CreateSingleLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="create_single.handler",
            code=_lambda.Code.from_asset("backend/post-content"),
            environment={
                "SINGLES_TABLE": table_singles.table_name,
                "AUDIO_BUCKET":  audio_bucket.bucket_name,
                "IMAGES_BUCKET": images_bucket.bucket_name,
            },
            #log_retention=logs.RetentionDays.ONE_WEEK
        )


        albums.add_method(
            "POST",
            apigw.LambdaIntegration(create_album_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer
        )
        
        singles.add_method(
            "POST",
            apigw.LambdaIntegration(create_single_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer
        )
        
        # permissions
        table_albums.grant_write_data(create_album_lambda)
        table_singles.grant_write_data(create_album_lambda)   # album lambda piše i single-ove
        table_singles.grant_write_data(create_single_lambda)

        audio_bucket.grant_read(create_album_lambda)    # za head_object
        images_bucket.grant_read(create_album_lambda)
        audio_bucket.grant_read(create_single_lambda)
        images_bucket.grant_read(create_single_lambda)

                
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


        feed = api.root.add_resource("feed",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=["GET", "OPTIONS"],
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
            ))

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

        # ----------------- SNS & Notifications -----------------

        new_content_topic = sns.Topic(
            self, "NewContentTopic",
            topic_name="new-content-topic"
        )

        notification_queue = sqs.Queue(
            self, "NotificationQueue",
            queue_name="notification-queue",
            removal_policy=RemovalPolicy.DESTROY
        )

        new_content_topic.add_subscription(
            sns_subscriptions.SqsSubscription(notification_queue)
        )

        send_notifications_lambda = _lambda.Function(
            self, "SendNotificationsLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="send_notifications.handler",
            code=_lambda.Code.from_asset("backend/lambdas/notifications"),
            environment={
                "SUBSCRIPTIONS_TABLE_NAME": table_subscriptions.table_name,
                "GSI_NAME": "by-target-id"
            }
        )

        send_notifications_lambda.add_event_source(
            lambda_event_sources.SqsEventSource(notification_queue)
        )

        table_subscriptions.grant_read_data(send_notifications_lambda)
        new_content_topic.grant_publish(create_artist_lambda)


        subscribe_lambda = _lambda.Function(
            self, "SubscribeLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="subscribe.handler",
            code=_lambda.Code.from_asset("backend/lambdas/subscriptions"),
            environment={
                "SUBSCRIPTIONS_TABLE_NAME": table_subscriptions.table_name
            }
        )
        table_subscriptions.grant_write_data(subscribe_lambda)

        unsubscribe_lambda = _lambda.Function(
            self, "UnsubscribeLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="unsubscribe.handler",
            code=_lambda.Code.from_asset("backend/lambdas/subscriptions"),
            environment={
                "SUBSCRIPTIONS_TABLE_NAME": table_subscriptions.table_name
            }
        )
        table_subscriptions.grant_write_data(unsubscribe_lambda)

        subscriptions_resource = api.root.add_resource(
            "subscriptions",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
                allow_headers=["Content-Type", "Authorization", "X-Api-Key"]
            )
        )

        get_subscriptions_lambda = _lambda.Function(
            self, "GetSubscriptionsLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="get_subscriptions.handler",
            code=_lambda.Code.from_asset("backend/lambdas/subscriptions"),
            environment={
                "SUBSCRIPTIONS_TABLE_NAME": table_subscriptions.table_name
            }
        )
        table_subscriptions.grant_read_data(get_subscriptions_lambda)

        subscriptions_resource.add_method(
            "GET",
            apigw.LambdaIntegration(get_subscriptions_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer
        )

        subscriptions_resource.add_method(
            "POST",
            apigw.LambdaIntegration(subscribe_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer
        )

        subscription_target_resource = subscriptions_resource.add_resource("{targetId}")
        subscription_target_resource.add_method(
            "DELETE",
            apigw.LambdaIntegration(unsubscribe_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer
        )
