LTI 1.3 Platform implementation
===============================

A+ supports selected parts of the LTI 1.3 platform implementation. In addition
to the [Core Specification](https://www.imsglobal.org/spec/lti/v1p3) and the
[Security Framework](https://www.imsglobal.org/spec/security/v1p0/), it
partially supports the [Assignment and Grade Service
specification](http://www.imsglobal.org/spec/lti-ags/v2p0) (AGS), so that the
points from external grading services can be submitted to A+. A+ does not
support querying the results from AGS interface, or adding or modifying
LTI's line items through the LTI API. Of the other commonly used features, the LTI 1.3
platform implementation does not, for the time being, support the [Deep Linking
Specification](https://www.imsglobal.org/spec/lti-dl/v2p0) or [Dynamic
Registration Specification](https://www.imsglobal.org/spec/lti-dr/v1p0).

The LTI 1.3 specification builds on
[OAuth2](https://www.rfc-editor.org/rfc/rfc6749.html) and [OpenID
Connect](https://openid.net/specs/openid-connect-core-1_0.html) specifications,
and the A+ LTI 1.3 platform implementation therefore uses the
[oauthlib](https://pypi.org/project/oauthlib/) for implementing the core
security features.


## Configuring a new LTI 1.3 Tool in A+

In order to take a new LTI 1.3 Tool into use, sysadmin needs to configure the
following settings in the Admin view, under *External_Services / LTI v1.3
services*. These settings should be provided by the tool provider.

* **URL** is the LTI launch URL from which the service is triggered.

* **Destination region** and **Privacy notice URL** are as with other external
  services, depending on whether the service is internal, inside EU or outside
  EU.

* **Menu label** and **Menu icon class** are visible in the side menu, if
  configured. The menu label is also referred to when configuring the LTI-based
  exercises.

* **Login initiation URL** is used when A+ LTI 1.3 platform implementation
  starts the authentication handshake with the tool, as specified in [Section
  5.1](https://www.imsglobal.org/spec/security/v1p0/#platform-originating-messages)
  of the Security Framework specification. The tool provider should provide the
  correct URL to use.

* **Client ID** identifies the tool in the LTI messages and should be unique for
  each tool configuration. A+ allows the system admin to select the identifier,
  and the exact format of the identifier is not limited in any way, as long as
  it is unique.

* **Deployment ID** allows separating different deployments for a particular
  client. Currently A+ does not have any functionality to support different
  deployments within a single client, but the configuration is included for
  protocol compliance, and for possible future use. The format of the deployment
  ID is free for the system admin to choose.

* **JWKS URL** is the address from which the tool's public key can be found in
  [JSON Web Key (JWK) format](https://www.rfc-editor.org/rfc/rfc7517.html). The
  tool administrators will provide this URL.

* **Share launcher's name, email and student ID** option controls whether A+ shares
  the user's real name, E-mail and student ID with the tool.


## LTI 1.3 configuration data shared with the tool provider

Also the LTI tool administrator needs to configure some details about A+ at the
tool's end. Typically, the following information is needed (the exact
terminology may vary depending on the tool):

* **Issuer (or platform ID)**: This is the issuer identifier, used in JWT tokens in
  LTI exchanges. With A+ this should be equal to the value of BASE_URL settings
  variable, for example "https://plus.cs.aalto.fi" in Aalto's production
  deployment.

* **Authentication request URL**: This is the address to which the tool sends its
  response to the login initiation message, as specified in [Section
  5.1](https://www.imsglobal.org/spec/security/v1p0/#platform-originating-messages)
  of the Security Framework specification. A+ uses "BASE_URL/lti/auth_login/" as
  the endpoint for receiving these messages, for example in Aalto's case
  "https://plus.cs.aalto.fi/lti/auth_login/".

* **Public keyset URL**: This is the URL where A+ deployment shares its public
  key in JSON Web Key format. A+ uses "BASE_URL/lti/jwks" as the endpoint, for
  example in Aalto's case "https://plus.cs.aalto.fi/lti/jwks".

* **Access token URL**: This URL is for the tool to request access token needed
  in different LTI messages, for example for updating the scores from the tool.
  A+ uses "BASE_URL/lti/token" as the endpoint, for example in Aalto's case
  "https://plus.cs.aalto.fi/lti/token"

In addition, the client ID (and often also the deployment ID) need to be
configured in the tool. These must be the same values as configured in the admin
view, as described above.


## Configuring LTI exercises and content

To include a service or exercise from the LTI Tool as an A+ exercise, the "lti1p3" directive
can be used in the course RST source, together with the label identifying the
LTI tool. This label must be equal to what was configured in the "Menu label"
setting in the A+ admin view.

Some services use LTI's custom parameters to identify more specifically which
part of the content at the tool's end is to be included. The "lti_custom"
directive allows the course creator to configure the custom parameters, based on
what the tool requires. More information and an example of the configuration is
available in [a-plus-rst-tools
documentation](https://github.com/apluslms/a-plus-rst-tools/blob/master/README.md).

An LTI 1.3 tool can also be configured to the A+ side menu in the "Edit Course"
view, similarly to LTI 1.1 services.


## Other information

It is possible to configure the lifetime of JWT tokens used in the LTI protocol
by using the `LTI_TOKEN_LIFETIME` settings variable. This defaults to 3600 seconds
(one hour).

If Apache is used to process HTTP requests at either end of the LTI session, it
should be noted that Apache configuration defaults to hiding the HTTP
Authorization headers from application logic, but the LTI implementation
requires access to these headers. Therefore, Apache's
[CGIPassAuth](https://httpd.apache.org/docs/2.4/en/mod/core.html#cgipassauth)
directive should be enabled in Apache configuration in order for LTI to work.
