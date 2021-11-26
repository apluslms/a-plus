# Authorization and Authentication protocol

Every request A+ makes to graders and other services contain a JWT
authentication/authorization token. Any request to A+ that requires
authentication must also contain a JWT. This does not include submission
grading, as then it includes a token in the GET parameters. Though, this token
can be sent as part of the JWT's tokens field.

The JWT is delivered in the Authorization header:

    Authorization: bearer <JWT>

The [aplus-auth][aplus-auth-git] python library can be used to
handle the nitty-gritty of this specification.

The following uses the word "party" to refer to anyone/anything that might want
to participate in communication.

## JWT structure

The JWT follows the specification [RFC7519](https://datatracker.ietf.org/doc/html/rfc7519).

The payload has the following fields:

    iss, string
        The public key of the party who signed this token.
    sub, string
        The party who made the HTTP request. This is either the public key of
        the requester, or "user:<id>" for normal A+ users.
    aud, string
        The public key of the party who the HTTP request is sent to.
    exp, JSON numeric value
        The expiration time of the token (seconds since epoch).
    permissions, list of permissions (see below)
        The permissions that the sub(ject) claims to have, and iss(uer) has
        verified (authorized).
    tokens (optional), list of strings
    + Any other fields but they are not checked by A+

Additionally, there are two special fields used when asking an authority
(generally A+) to sign a token for them:

    taud, string
        The public key of the party who is to be the audience of the new token.
    turl, string
        The URL of the party who is to be the audience of the new token. This
        requires the authority to know what the public key of said URL is.

## JWT verification

A receiver should reject a request if

- the aud does not match the receiver's public key
- the receiver does not recognize the issuer public key
- the signature cannot be verified using the issuer public key
- any of the permission claims is invalid: a claim is invalid if
    - the issuer does not have the authority to authorize the claim, and
    - the receiver cannot verify the claim themselves (either does not
    have the required information, or the claim is simply false)
- the expiration time has passed
- any of the tokens are invalid

## Token signing request

A token signing request is a JWT that includes one of the special fields in
[JWT structure](#JWT-structure).

A party may send a token signing request to any party that supports it (called
an authority) (generally A+). In this case, the authority verifies the JWT
(in particular, the authority most likely must verify the permissions themselves)
and, in the case that the JWT passes verification, swaps the iss and aud fields
of the payload and signs it with their own private key. The result is a token
where the authority is the issuer, the requester is the subject, the audience
is the target specified in the signing request, and the permissions are
unchanged. The token is returned as text in the HTTP response body.

This allows two parties that do not trust each other to use a third party
(authority) to verify the permission claims.

## Permission claims

### Specification

Each claim is JSON with the format `[permission_type, permission, details]`.

The first element, `permission_type`, is a string: one of "course", "instance",
"module", "exercise" and "submission". The only type that A+ currently verifies
is "instance".

The second element, `permission`, is a number with the following meanings:

    NONE: 0
    READ: 1
    WRITE: 2
    CREATE: 4

Note that 0 means no permission: there is no point in including a claim with
it in the permission list. It is reserved purely for internal (to the party)
use.

The third element, `details`, is a dictionary containing the identifying
details of the object. Generally, these can be any `key: value` pairs that are
found in the database for the model type in question. Note that this means that
the dictionary does not need to identify a single object, it can also match
multiple, in which case the permission is checked against every object. If any
of the objects fail the check, the whole claim is rejected. For any deviations
from this general rule, see [below](#How-to-get-permissions).

### How to get permissions

The only type of claim that A+ currently verifies (and possibly accepts) is
"instance" with READ or WRITE permission. For this, the requester needs to be
set as the `configure_url` of the instance. The `URL_TO_ALIAS` and
`ALIAS_TO_PUBLIC_KEY` settings are used to determine the public key of the URL
in `configure_url`.

## X <-> A+ communication

Both X and A+ need to know each other public keys. When one makes a request to
the other, they construct the approriate JWT with the appropriate permission
claims and sign it with their own private key.

## X -> Y communication

If Y knows X's public key and can verify the permission claims itself, X can
proceed as in X -> A+ communication

If Y doesn't know X's public key or cannot verify the permission claims itself,
X needs to first send a token signing request to A+ and then use the returned
token to make its request to Y. The token signing request contains the same
permissions as what would be sent to Y and has Y's information in either the
`turl` or `taud` field.


[aplus-auth-git]: https://github.com/lainets/aplus-auth
