from slackclient import SlackClient

from dagster import resource, seven, Dict, Field, String


class SlackConnection:
    def __init__(self, token):
        self.token = token
        self.sc = SlackClient(self.token)

        class _Chat:
            @classmethod
            def post_message(
                cls,
                channel='#noise',
                username='dagsterbot',
                text='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                # pylint: disable=line-too-long
                icon_url='https://user-images.githubusercontent.com/609349/56463858-9d2eab80-6391-11e9-8288-e606fdf674b5.png',
                attachments=None,
            ):
                '''slack_resource.chat.post_message() : chat.postMessage

                See https://api.slack.com/methods/chat.postMessage
                '''
                api_params = {
                    'channel': channel,
                    'username': username,
                    'text': text,
                    'icon_url': icon_url,
                    'attachments': seven.json.dumps(attachments),
                }
                return self.sc.api_call('chat.postMessage', **api_params)

        self.chat = _Chat()

    def api_call(self, method, timeout=None, **kwargs):
        return self.sc.api_call(method, timeout, **kwargs)


@resource(
    config_field=Field(
        Dict(
            {
                'token': Field(
                    String,
                    description='''To configure access to the Slack API, you'll need an access
                    token provisioned with access to your Slack workspace.

                    Tokens are typically either user tokens or bot tokens. For programmatic posting
                    to Slack from this resource, you probably want to provision and use a bot token.

                    More in the Slack API documentation here: https://api.slack.com/docs/token-types
                    ''',
                )
            }
        )
    ),
    description='This resource is for connecting to Slack',
)
def slack_resource(context):
    return SlackConnection(context.resource_config.get('token'))
