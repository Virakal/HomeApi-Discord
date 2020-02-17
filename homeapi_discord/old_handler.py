OAUTH_LOGIN_URL = 'http://localhost:8069/oauth2'

class Handler(BaseHTTPRequestHandler):
	route_handlers = {
		'/': 'handle_root',
		'/login': 'handle_login',
		'/oauth2': 'handle_oauth'
	}

	scopes = ' '.join(DISCORD_CLIENT_SCOPES)
	client_id = DISCORD_CLIENT_ID

	with open('./homeapi_discord/secret.txt', 'r') as f:
		client_secret = f.readline().strip()

	redirect_url = 'http://localhost:8069/login'
	login_url = OAUTH_LOGIN_URL

	def do_GET(self):
		url = urlparse(self.path)
		if url.path in self.route_handlers:
			method = getattr(self, self.route_handlers[url.path])
			method(dict(parse_qsl(url.query)))
		else:
			self.send_response(404)

	def success(func):
		def wrapper(self, *args, **kwargs):
			self.send_response(200)
			self.send_header('Content-type', 'text/html')
			self.log_message(self.path)
			self.end_headers()
			return func(self, *args, **kwargs)
		return wrapper

	@success
	def handle_root(self, data):
		self.wfile.write('Waiting to login to Discord'.encode('utf-8'))

	def handle_oauth(self, data):
		self.send_response(302)
		c = Client(auth_endpoint='https://discordapp.com/api/oauth2/authorize',
				   client_id=self.client_id)
		self.send_header('Location', c.auth_uri(
			scope=self.scopes, access_type='offline',
			redirect_uri=self.redirect_url))
		self.end_headers()

	@success
	def handle_login(self, data):
		c = Client(token_endpoint='https://discordapp.com/api/oauth2/token',
				   resource_endpoint='https://discordapp.com/api/oauth2/',
				   client_id=self.client_id,
				   client_secret=self.client_secret,
				   token_transport=transport_headers)
		c.request_token(code=data['code'],
						redirect_uri=self.redirect_url)

		self.dump_client(c)
		data = c.request('/userinfo')
		self.dump_response(data)

		if hasattr(c, 'refresh_token'):
			rc = Client(token_endpoint=c.token_endpoint,
						client_id=c.client_id,
						client_secret=c.client_secret,
						resource_endpoint=c.resource_endpoint,
						token_transport='headers')

			rc.request_token(grant_type='refresh_token',
							 refresh_token=c.refresh_token)
			self.wfile.write('<p>post refresh token:</p>'.encode('utf-8'))
			self.dump_client(rc)

def discord_login():
	server_address = ('', 8069)
	print(f"Login at {OAUTH_LOGIN_URL}")
	server = HTTPServer(server_address, Handler)
	server.timeout = 60
	server.serve_forever()
