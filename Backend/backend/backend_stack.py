from constructs import Construct
from aws_cdk import (
    RemovalPolicy,
    Stack,
    Duration,
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
    aws_logs as logs,
    CfnOutput
)

import uuid

class BackendStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        update_feed_added_content_queue = sqs.Queue(
            self, "UpdateFeedAddedContentQueue",
            removal_policy=RemovalPolicy.DESTROY
        )

        update_feed_score_specific_user_queue = sqs.Queue(
            self, "UpdateFeedScoreSpecificUserQueue",
            removal_policy=RemovalPolicy.DESTROY
        )

        update_feed_specific_user_queue = sqs.Queue(
            self, "UpdateFeedSpecificUserQueue",
            removal_policy=RemovalPolicy.DESTROY
        )
        
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

        user_pool_client = cognito.UserPoolClient(
            self, "NewUserPoolClient",
            user_pool=self.user_pool,
            auth_flows=cognito.AuthFlow(
                user_srp=True
             )
        )

        CfnOutput(self, "UserPoolClientId", value=user_pool_client.user_pool_client_id)

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

        new_content_topic = sns.Topic(
            self, "NewContentTopic",
            topic_name="new-content-topic"
        )

        table_activity = dynamodb.Table(
            self, "Activity",
            partition_key=dynamodb.Attribute(name="username", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="accessTime", type=dynamodb.AttributeType.STRING),  # store datetime as ISO string
            removal_policy=RemovalPolicy.DESTROY
        )

        table_ratings = dynamodb.Table(
            self, "Ratings",
            partition_key=dynamodb.Attribute(name="contentId", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="username", type=dynamodb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY # Koristite DESTROY samo u razvoju!
        )

        # 2. GSI: Index za pretragu SVIH ocena po korisniku
        table_ratings.add_global_secondary_index(
            index_name="UserRatingsIndex",
            partition_key=dynamodb.Attribute(name="username", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="contentId", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL
        )
        self.table_ratings_name = table_ratings.table_name
        
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

        table_genres = dynamodb.Table(
            self, "Genres",
            partition_key=dynamodb.Attribute(name="genreId", type=dynamodb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY
        )

        
        table_albums = dynamodb.Table(self, "Albums",
            # Primarni ključ je sada Composite (PK: artistId, SK: albumId)
            partition_key=dynamodb.Attribute(name="artistId", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="albumId", type=dynamodb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY
        )
        
        table_singles = dynamodb.Table(self, "Singles",
            # Primarni ključ je sada Composite (PK: artistId, SK: singleId)
            partition_key=dynamodb.Attribute(name="artistId", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="singleId", type=dynamodb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY
        )
        
        table_singles.add_global_secondary_index(
            index_name="by-album-id",
            partition_key=dynamodb.Attribute(name="albumId", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="singleId", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL
        )

        table_genre_index = dynamodb.Table(
            self, 'GenreIndex',
            partition_key=dynamodb.Attribute(name='genreName', type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name='contentKey', type=dynamodb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY
        )

        filter_by_genre_lambda = _lambda.Function(
            self, 'FilterByGenreLambda',
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler='filter_by_genre.handler',
            code=_lambda.Code.from_asset("backend/lambdas/content"),
            environment={
                'GENRE_INDEX_TABLE': table_genre_index.table_name
            }
        )

        table_genre_index.grant_read_data(filter_by_genre_lambda)

        table_artist_index = dynamodb.Table(
            self, 'ArtistIndex',
            partition_key=dynamodb.Attribute(name='artistId', type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name='contentKey', type=dynamodb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY
        )

        filter_by_artist_lambda = _lambda.Function(
            self, 'FilterByArtistLambda',
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler='filter_by_artist.handler',
            code=_lambda.Code.from_asset("backend/lambdas/content"),
            environment={
                'ARTIST_INDEX_TABLE': table_artist_index.table_name
            }
        )

        table_artist_index.grant_read_data(filter_by_artist_lambda)

        filter_add_lambda = _lambda.Function(
            self, 'FilterAddLambda',
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler='create_filter.handler',
            code=_lambda.Code.from_asset("backend/lambdas/content"),
            environment={
                'ARTIST_INDEX_TABLE': table_artist_index.table_name,
                'GENRE_INDEX_TABLE': table_genre_index.table_name
            }
        )

        table_artist_index.grant_write_data(filter_add_lambda)
        table_genre_index.grant_write_data(filter_add_lambda)
        
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
            block_public_access=s3.BlockPublicAccess.BLOCK_ACLS_ONLY,
            cors=[
                s3.CorsRule(
                    allowed_methods=[
                        s3.HttpMethods.PUT,
                        s3.HttpMethods.POST,
                        s3.HttpMethods.GET,
                        s3.HttpMethods.HEAD,
                    ],
                    allowed_origins=["http://localhost:4200"],
                    allowed_headers=["*"],
                    exposed_headers=["ETag"]
            )]
        )

        artist_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject"],
                resources=[f"arn:aws:s3:::{artist_bucket.bucket_name}/*"],
                effect=iam.Effect.ALLOW,
                principals=[iam.ArnPrincipal("*")]
            )
        )

        create_artist_lambda = _lambda.Function(
            self, "CreateArtistLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="create_artist.handler",
            code=_lambda.Code.from_asset("backend/lambdas/content"),
            environment={
                "BUCKET_NAME": artist_bucket.bucket_name,
                "TABLE_NAME": table_artists.table_name,
                "FILTER_ADD_LAMBDA": filter_add_lambda.function_name,
                "QUEUE_URL": update_feed_added_content_queue.queue_url,
            }
        )
        filter_add_lambda.grant_invoke(create_artist_lambda)

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

        filter_genre_resource = api.root.add_resource(
            "filter-genre",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=["GET", "OPTIONS"],
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
            )
        )

        filter_genre_resource.add_method(
            "GET",
            apigw.LambdaIntegration(filter_by_genre_lambda)
        )

        filter_artist_resource = api.root.add_resource(
            "filter-artist",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=["GET", "OPTIONS"],
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
            )
        )

        filter_artist_resource.add_method(
            "GET",
            apigw.LambdaIntegration(filter_by_artist_lambda)
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
                allow_methods=["GET", "POST" ,"DELETE", "OPTIONS"],
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
            ))

        artists.add_method(
            "POST",
            apigw.LambdaIntegration(create_artist_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer
        )

        get_artist_lambda = _lambda.Function(
            self, "GetArtistLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="get_artist.handler",
            code=_lambda.Code.from_asset("backend/lambdas/content"),
            environment={
                "ARTIST_TABLE": table_artists.table_name,
                "RATINGS_TABLE": table_ratings.table_name,
                "QUEUE_URL": update_feed_score_specific_user_queue.queue_url
            }
        )
        table_artists.grant_read_data(get_artist_lambda)
        table_ratings.grant_read_data(get_artist_lambda)
        
        get_artist = api.root.add_resource("get-artist",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=["GET", "OPTIONS"],
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
            ))

        get_artist.add_method(
            "GET",
            apigw.LambdaIntegration(get_artist_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer
        )
        
        get_artists_lambda = _lambda.Function(
            self, "GetArtistsLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="get_artists.handler",
            code=_lambda.Code.from_asset("backend/lambdas/content"), 
            environment={
                "ARTISTS_TABLE_NAME": table_artists.table_name # Koristi ime tabele
            }
        )
        table_artists.grant_read_data(get_artists_lambda)    
        get_artists_all = api.root.add_resource("artists-all",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=["GET", "OPTIONS"],
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
            )
        )

        get_artists_all.add_method(
            "GET",
            apigw.LambdaIntegration(get_artists_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer
        )
        
        albums = api.root.add_resource("albums",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=["GET", "POST","PUT","DELETE", "OPTIONS"],
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
            ))

        singles = api.root.add_resource("singles",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
            ))
        
        get_single_lambda = _lambda.Function(
            self, "GetSingleLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="get_single.handler",
            code=_lambda.Code.from_asset("backend/lambdas/content"),
            environment={
                "SINGLE_TABLE": table_singles.table_name,
                "RATINGS_TABLE": table_ratings.table_name,
                "QUEUE_URL": update_feed_score_specific_user_queue.queue_url
            }
        )
        table_singles.grant_read_data(get_single_lambda)
        table_ratings.grant_read_data(get_single_lambda)
        
        get_single = api.root.add_resource("get-single",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=["GET", "OPTIONS"],
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
            ))

        get_single.add_method(
            "GET",
            apigw.LambdaIntegration(get_single_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer
        )

        get_album_lambda = _lambda.Function(
            self, "GetAlbumLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="get_album.handler",
            code=_lambda.Code.from_asset("backend/lambdas/content"),
            environment={
                "ALBUM_TABLE": table_albums.table_name,
                "RATINGS_TABLE": table_ratings.table_name,
                "QUEUE_URL": update_feed_score_specific_user_queue.queue_url
            }
        )
        table_albums.grant_read_data(get_album_lambda)
        table_ratings.grant_read_data(get_album_lambda)

        get_album = api.root.add_resource("get-album",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=["GET", "OPTIONS"],
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
            ))

        get_album.add_method(
            "GET",
            apigw.LambdaIntegration(get_album_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer
        )
        
        get_singles_by_album_lambda = _lambda.Function(
            self, "GetSinglesByAlbumLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="get_singles_by_album.handler",
            code=_lambda.Code.from_asset("backend/lambdas/content"),
            environment={
                "SINGLE_TABLE": table_singles.table_name,
                "SINGLES_GSI": "by-album-id"
            }
        )
        table_singles.grant_read_data(get_singles_by_album_lambda)

        get_album_songs = api.root.add_resource("get-album-songs",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=["GET", "OPTIONS"],
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
            ))

        get_album_songs.add_method(
            "GET",
            apigw.LambdaIntegration(get_singles_by_album_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer
        )

        audio_bucket = s3.Bucket(
            self, "SongFilesBucket",
            bucket_name=f"audio-files-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ACLS_ONLY,
            cors=[
                s3.CorsRule(
                    allowed_methods=[
                        s3.HttpMethods.PUT,
                        s3.HttpMethods.POST,
                        s3.HttpMethods.GET,
                        s3.HttpMethods.HEAD,
                    ],
                    allowed_origins=["*"],#allowed_origins=["http://localhost:4200"],
                    allowed_headers=["*"],
                    exposed_headers=["ETag"]
                )
            ]
        )

        audio_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject"],
                resources=[f"arn:aws:s3:::{audio_bucket.bucket_name}/*"],
                effect=iam.Effect.ALLOW,
                principals=[iam.ArnPrincipal("*")]
            )
        )
        
        images_bucket = s3.Bucket(
            self, "SongImagesBucket",
            bucket_name=f"song-images-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ACLS_ONLY,
            cors=[
                s3.CorsRule(
                    allowed_methods=[
                        s3.HttpMethods.PUT,
                        s3.HttpMethods.POST,
                        s3.HttpMethods.GET,
                        s3.HttpMethods.HEAD,
                    ],
                    allowed_origins=["http://localhost:4200"],
                    allowed_headers=["*"],
                    exposed_headers=["ETag"]
                )
            ]
        )

        images_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject"],
                resources=[f"arn:aws:s3:::{images_bucket.bucket_name}/*"],
                effect=iam.Effect.ALLOW,
                principals=[iam.ArnPrincipal("*")]
            )
        )
        
        # audio_bucket.add_cors_rule(
        #     allowed_methods=[s3.HttpMethods.PUT, s3.HttpMethods.GET, s3.HttpMethods.HEAD],
        #     allowed_origins=["http://localhost:4200"],   # or "*" for quick dev
        #     allowed_headers=["*"],
        #     expose_headers=["ETag"],
        #     max_age=3000,
        # )
        # images_bucket.add_cors_rule(
        #     allowed_methods=[s3.HttpMethods.PUT, s3.HttpMethods.GET, s3.HttpMethods.HEAD],
        #     allowed_origins=["http://localhost:4200"],   # or "*"
        #     allowed_headers=["*"],
        #     expose_headers=["ETag"],
        #     max_age=3000,
        # )
        # NEW create_album_lambda
        
        # ------------- RATING -----------------
        rate_content_lambda = _lambda.Function(
            self, "RateContentLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="rate_content.handler",
            code=_lambda.Code.from_asset("backend/lambdas/content"), # Pretpostavljamo da je putanja backend/ratings
            timeout=Duration.seconds(10),
            environment={
                "RATINGS_TABLE": table_ratings.table_name,
                "SINGLES_TABLE": table_singles.table_name, # Potrebno za dohvatanje žanrova
                "ALBUMS_TABLE": table_albums.table_name,   # Potrebno za dohvatanje žanrova
                "QUEUE_URL": update_feed_score_specific_user_queue.queue_url,
            }
        )

        # 4. Dozvole
        table_ratings.grant_read_write_data(rate_content_lambda)
        table_singles.grant_read_data(rate_content_lambda) # Dozvola za čitanje zbog žanrova
        table_albums.grant_read_data(rate_content_lambda) # Dozvola za čitanje zbog žanrova


        # 5. API Gateway Integracija
        ratings_resource = api.root.add_resource(
            "ratings",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=["POST", "OPTIONS"],
                allow_headers=apigw.Cors.DEFAULT_HEADERS
            )
        )

        ratings_resource.add_method(
            "POST",
            apigw.LambdaIntegration(rate_content_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer,
        )
        # ------------- RATING END ----------------- 
        
        table_singles.add_global_secondary_index(
            index_name="SingleIdIndexV2", 
            partition_key=dynamodb.Attribute(name="singleId", type=dynamodb.AttributeType.STRING), 
            projection_type=dynamodb.ProjectionType.ALL 
        )       
        
        table_albums.add_global_secondary_index(
            index_name="AlbumIdIndexV2", 
            partition_key=dynamodb.Attribute(name="albumId", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL  
        )
        # ------------- GSI ZA ALBUM/SINGLE ----------------- 
        
        delete_single_lambda = _lambda.Function(
            self, "DeleteSingleLambda",
            function_name="DeleteSingleLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="delete_single.handler", # Ovo će biti fajl backend/lambdas/content/delete_single.py
            code=_lambda.Code.from_asset("backend/lambdas/content"),
            timeout= Duration.seconds(10), # dodati import cdk gore ako nije
            environment={
                "SINGLES_TABLE": table_singles.table_name,
                "AUDIO_BUCKET": audio_bucket.bucket_name,
                "IMAGES_BUCKET": images_bucket.bucket_name,
                # Za kompleksno brisanje (brisati i iz indexa)
                "GENRE_INDEX_TABLE": table_genre_index.table_name, 
                "ARTIST_INDEX_TABLE": table_artist_index.table_name,
            }
        )
        
        # Dozvole za DynamoDB i S3
        table_singles.grant_write_data(delete_single_lambda) # Dozvola za DELETE ITEM iz Singles
        table_singles.grant_read_data(delete_single_lambda)
        audio_bucket.grant_delete(delete_single_lambda)      # Dozvola za s3:DeleteObject iz audio bucketa
        images_bucket.grant_delete(delete_single_lambda)     # Dozvola za s3:DeleteObject iz image bucketa

        # Dozvole za brisanje iz filter indexa (GenreIndex i ArtistIndex)
        table_genre_index.grant_write_data(delete_single_lambda)
        table_artist_index.grant_write_data(delete_single_lambda)
        
        # Kreiranje podresursa /singles/{singleId}
        single_id_resource = singles.add_resource("{singleId}",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=["GET", "DELETE", "OPTIONS"], # Definisanje dozvoljenih metoda na ovom resursu
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
            ))

        # Povezivanje DELETE metode na /singles/{singleId} sa DeleteSingleLambda
        single_id_resource.add_method(
            "DELETE",
            apigw.LambdaIntegration(delete_single_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer
        )
        
        delete_album_lambda = _lambda.Function(
            self, "DeleteAlbumLambda",
            function_name="DeleteAlbumLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="delete_album.handler",
            code=_lambda.Code.from_asset("backend/lambdas/content"),
            timeout=Duration.seconds(30), # Duže vreme, jer radi kaskadno brisanje
            environment={
                "ALBUMS_TABLE": table_albums.table_name,
                "SINGLES_TABLE": table_singles.table_name, # Potrebno za brisanje singlova
                "AUDIO_BUCKET": audio_bucket.bucket_name,
                "IMAGES_BUCKET": images_bucket.bucket_name,
                "GENRE_INDEX_TABLE": table_genre_index.table_name,
                "ARTIST_INDEX_TABLE": table_artist_index.table_name,
            }
        )

        # 2. Dozvole
        # A. Dozvole za ALBUMS tabelu (Čitanje i Brisanje)
        table_albums.grant_read_data(delete_album_lambda)
        table_albums.grant_write_data(delete_album_lambda)
        
        # B. Dozvole za SINGLES tabelu (Čitanje/Query i Brisanje)
        table_singles.grant_read_data(delete_album_lambda) 
        table_singles.grant_write_data(delete_album_lambda)
        # Dozvola za Query na GSI-ju 'AlbumIndex' (Ako je GSI na Singles)
        delete_album_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["dynamodb:Query"],
                resources=[f"{table_singles.table_arn}/index/*"] # Dozvola za query na svim indeksima
            )
        )

        # C. Dozvole za S3, Indekse
        images_bucket.grant_delete(delete_album_lambda)
        audio_bucket.grant_delete(delete_album_lambda)
        table_genre_index.grant_write_data(delete_album_lambda)
        table_artist_index.grant_write_data(delete_album_lambda)
        
        album_id_resource = albums.add_resource("{albumId}",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=["GET", "DELETE", "OPTIONS"],
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
            ))

        # Povezivanje DELETE metode na /albums/{albumId} sa DeleteAlbumLambda
        album_id_resource.add_method(
            "DELETE",
            apigw.LambdaIntegration(delete_album_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer
        )
        
        # 1. Definicija Lambda funkcije za brisanje umetnika
        delete_artist_lambda = _lambda.Function(
            self, "DeleteArtistLambda",
            function_name="DeleteArtistLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="delete_artist.handler",
            code=_lambda.Code.from_asset("backend/lambdas/content"),
            timeout=Duration.seconds(45), # Još duže vreme zbog višestrukog kaskadnog brisanja
            environment={
                "ARTISTS_TABLE": table_artists.table_name,
                "ALBUMS_TABLE": table_albums.table_name,
                "SINGLES_TABLE": table_singles.table_name,
                "AUDIO_BUCKET": audio_bucket.bucket_name,
                "IMAGES_BUCKET": images_bucket.bucket_name,
                "GENRE_INDEX_TABLE": table_genre_index.table_name,
                "ARTIST_INDEX_TABLE": table_artist_index.table_name,
            }
        )

        # 2. Dozvole
        
        # A. Dozvole za ARTISTS tabelu (Read/Write)
        table_artists.grant_read_data(delete_artist_lambda)
        table_artists.grant_write_data(delete_artist_lambda)
        
        # B. Dozvole za ALBUMS tabelu (Read/Query i Write/Delete)
        table_albums.grant_read_data(delete_artist_lambda)
        table_albums.grant_write_data(delete_artist_lambda)
        # Query na Albums GSI (za albume tog umetnika)
        delete_artist_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["dynamodb:Query"],
                resources=[f"{table_albums.table_arn}/index/*"] 
            )
        )
        
        # C. Dozvole za SINGLES tabelu (Read/Query i Write/Delete)
        table_singles.grant_read_data(delete_artist_lambda) 
        table_singles.grant_write_data(delete_artist_lambda)
        # Query na Singles GSI (za singlove tog umetnika)
        delete_artist_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["dynamodb:Query"],
                resources=[f"{table_singles.table_arn}/index/*"] 
            )
        )

        # D. Dozvole za S3, Indekse
        images_bucket.grant_delete(delete_artist_lambda)
        audio_bucket.grant_delete(delete_artist_lambda)
        table_genre_index.grant_write_data(delete_artist_lambda)
        table_artist_index.grant_write_data(delete_artist_lambda)
        
        artist_id_resource = artists.add_resource("{artistId}",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=["GET", "DELETE", "OPTIONS"],
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
            ))

        # Povezivanje DELETE metode na /artists/{artistId} sa DeleteArtistLambda
        artist_id_resource.add_method(
            "DELETE",
            apigw.LambdaIntegration(delete_artist_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer
        )
        
        
        create_album_lambda = _lambda.Function(
            self, "CreateAlbumLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="create_album.handler",
            code=_lambda.Code.from_asset("backend/post-content"),
            environment={
                "ALBUMS_TABLE":  table_albums.table_name, # umesto albums.table_name
                "SINGLES_TABLE": table_singles.table_name,  # umesto singles.table_name
                "AUDIO_BUCKET":  audio_bucket.bucket_name,
                "IMAGES_BUCKET": images_bucket.bucket_name,
                "GENRE_INDEX_TABLE": table_genre_index.table_name,
                "FILTER_ADD_LAMBDA": filter_add_lambda.function_name,
                "NEW_CONTENT_TOPIC_ARN": new_content_topic.topic_arn,
                "QUEUE_URL": update_feed_added_content_queue.queue_url,
            },
            #log_retention=logs.RetentionDays.ONE_WEEK
        )
        filter_add_lambda.grant_invoke(create_album_lambda)
        new_content_topic.grant_publish(create_album_lambda)

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
                "FILTER_ADD_LAMBDA": filter_add_lambda.function_name,
                "NEW_CONTENT_TOPIC_ARN": new_content_topic.topic_arn,
                "QUEUE_URL": update_feed_added_content_queue.queue_url,
            },
            #log_retention=logs.RetentionDays.ONE_WEEK
        )
        filter_add_lambda.grant_invoke(create_single_lambda)
        new_content_topic.grant_publish(create_single_lambda)

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

        # ----------------- SQS -----------------

        update_feed_score_specific_user_lambda = _lambda.Function(
            self, "UpdateFeedScoreSpecificUserLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="update_feed_score_specific_user.handler",
            code=_lambda.Code.from_asset("backend/lambdas/feed"),
            environment={
                "SCORE_TABLE_NAME" : table_score_cache.table_name,
                "QUEUE_URL": update_feed_specific_user_queue.queue_url
            }
        )

        table_score_cache.grant_read_write_data(update_feed_score_specific_user_lambda)

        update_feed_specific_user_lambda = _lambda.Function(
            self, "UpdateFeedSpecificUserLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="update_feed_specific_user.handler",
            code=_lambda.Code.from_asset("backend/lambdas/feed"),
            environment={
                "SCORE_TABLE_NAME" : table_score_cache.table_name,
                "FEED_TABLE_NAME" : table_feed_cache.table_name,
                "ARTIST_TABLE_NAME" : table_artists.table_name,
                "SINGLE_TABLE_NAME" : table_singles.table_name,
                "ALBUM_TABLE_NAME" : table_albums.table_name,
            }
        )

        table_score_cache.grant_read_data(update_feed_specific_user_lambda)
        table_feed_cache.grant_read_write_data(update_feed_specific_user_lambda)
        table_artists.grant_read_data(update_feed_specific_user_lambda)
        table_singles.grant_read_data(update_feed_specific_user_lambda)
        table_albums.grant_read_data(update_feed_specific_user_lambda)


        # ----------------- SNS & Notifications -----------------


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
                "GSI_NAME": "by-target-id",
                "USER_POOL_ID": self.user_pool.user_pool_id,
                "ARTISTS_TABLE_NAME": table_artists.table_name
            }
        )

        table_artists.grant_read_data(send_notifications_lambda)

        send_notifications_lambda.add_event_source(
            lambda_event_sources.SqsEventSource(notification_queue)
        )

        send_notifications_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["cognito-idp:AdminGetUser"],
                resources=[self.user_pool.user_pool_arn]
            )
        )

        send_notifications_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ses:SendEmail"],
                resources=["*"]
            )
        )

        table_subscriptions.grant_read_data(send_notifications_lambda)
        new_content_topic.grant_publish(create_artist_lambda)


        subscribe_lambda = _lambda.Function(
            self, "SubscribeLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="subscribe.handler",
            code=_lambda.Code.from_asset("backend/lambdas/subscriptions"),
            environment={
                "SUBSCRIPTIONS_TABLE_NAME": table_subscriptions.table_name,
                "QUEUE_URL": update_feed_score_specific_user_queue.queue_url
            }
        )
        table_subscriptions.grant_write_data(subscribe_lambda)

        unsubscribe_lambda = _lambda.Function(
            self, "UnsubscribeLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="unsubscribe.handler",
            code=_lambda.Code.from_asset("backend/lambdas/subscriptions"),
            environment={
                "SUBSCRIPTIONS_TABLE_NAME": table_subscriptions.table_name,
                "QUEUE_URL": update_feed_score_specific_user_queue.queue_url,
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

        update_feed_added_content_queue.grant_consume_messages(update_feed_added_content_lambda)
        update_feed_added_content_queue.grant_send_messages(create_artist_lambda)
        update_feed_added_content_queue.grant_send_messages(create_single_lambda)
        update_feed_added_content_queue.grant_send_messages(create_album_lambda)
        

        update_feed_added_content_lambda.add_event_source(
            lambda_event_sources.SqsEventSource(update_feed_added_content_queue)
        )
        
        

        update_feed_score_specific_user_queue.grant_consume_messages(update_feed_score_specific_user_lambda)
        update_feed_score_specific_user_queue.grant_send_messages(get_single_lambda)
        update_feed_score_specific_user_queue.grant_send_messages(get_artist_lambda)
        update_feed_score_specific_user_queue.grant_send_messages(get_album_lambda)
        update_feed_score_specific_user_queue.grant_send_messages(rate_content_lambda)
        update_feed_score_specific_user_queue.grant_send_messages(subscribe_lambda)
        update_feed_score_specific_user_queue.grant_send_messages(unsubscribe_lambda)

        update_feed_score_specific_user_lambda.add_event_source(
            lambda_event_sources.SqsEventSource(update_feed_score_specific_user_queue)
        )
        

        update_feed_specific_user_queue.grant_consume_messages(update_feed_specific_user_lambda)
        update_feed_specific_user_queue.grant_send_messages(update_feed_score_specific_user_lambda)

        update_feed_specific_user_lambda.add_event_source(
            lambda_event_sources.SqsEventSource(update_feed_specific_user_queue)
        )


        # test_s3_write_lambda = _lambda.Function(
        #     self, "TestS3WriteLambda",
        #     runtime=_lambda.Runtime.PYTHON_3_9,
        #     handler="test_s3_write.handler",
        #     code=_lambda.Code.from_asset("backend/post-content"), # Novi folder
        #     environment={
        #         "AUDIO_BUCKET": audio_bucket.bucket_name
        #     }
        # )
        # audio_bucket.grant_put(test_s3_write_lambda)

        # test_s3_resource = api.root.add_resource(
        #     "test-s3-write",
        #     default_cors_preflight_options=apigw.CorsOptions(
        #         allow_origins=apigw.Cors.ALL_ORIGINS,
        #         allow_methods=["POST", "OPTIONS"],
        #         allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
        #     )
        # )

        # test_s3_resource.add_method(
        #     "POST",
        #     apigw.LambdaIntegration(test_s3_write_lambda),
        #     authorization_type=apigw.AuthorizationType.COGNITO,
        #     authorizer=authorizer
        # )
