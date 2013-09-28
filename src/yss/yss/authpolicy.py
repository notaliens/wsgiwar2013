import warnings

from pyramid.interfaces import IAuthenticationPolicy
from pyramid.authentication import AuthTktCookieHelper
from pyramid.security import Authenticated
from pyramid.security import Everyone
from substanced.interfaces import IUserLocator
from substanced.principal import DefaultUserLocator
from zope.interface import implementer

Identified = 'system.Identified'

_marker = object()

@implementer(IAuthenticationPolicy)
class YSSAuthenticationPolicy(object):
    """A :app:`Pyramid` :term:`authentication policy`.

    Obtains data from a Pyramid "auth ticket" cookie.

    Allows for users who are *identified* (have valid credentials) but
    not *authenticated* (can be verified against a real user object in
    the 'principals' service).

    Constructor Arguments

    ``secret``

       The secret (a string) used for auth_tkt cookie signing.
       Required.

    ``cookie_name``

       Default: ``auth_tkt``.  The cookie name used
       (string).  Optional.

    ``secure``

       Default: ``False``.  Only send the cookie back over a secure
       conn.  Optional.

    ``include_ip``

       Default: ``False``.  Make the requesting IP address part of
       the authentication data in the cookie.  Optional.

    ``timeout``

       Default: ``None``.  Maximum number of seconds which a newly
       issued ticket will be considered valid.  After this amount of
       time, the ticket will expire (effectively logging the user
       out).  If this value is ``None``, the ticket never expires.
       Optional.

    ``reissue_time``

       Default: ``None``.  If this parameter is set, it represents the number
       of seconds that must pass before an authentication token cookie is
       automatically reissued as the result of a request which requires
       authentication.  The duration is measured as the number of seconds
       since the last auth_tkt cookie was issued and 'now'.  If this value is
       ``0``, a new ticket cookie will be reissued on every request which
       requires authentication.

       A good rule of thumb: if you want auto-expired cookies based on
       inactivity: set the ``timeout`` value to 1200 (20 mins) and set the
       ``reissue_time`` value to perhaps a tenth of the ``timeout`` value
       (120 or 2 mins).  It's nonsensical to set the ``timeout`` value lower
       than the ``reissue_time`` value, as the ticket will never be reissued
       if so.  However, such a configuration is not explicitly prevented.

       Optional.

    ``max_age``

       Default: ``None``.  The max age of the auth_tkt cookie, in
       seconds.  This differs from ``timeout`` inasmuch as ``timeout``
       represents the lifetime of the ticket contained in the cookie,
       while this value represents the lifetime of the cookie itself.
       When this value is set, the cookie's ``Max-Age`` and
       ``Expires`` settings will be set, allowing the auth_tkt cookie
       to last between browser sessions.  It is typically nonsensical
       to set this to a value that is lower than ``timeout`` or
       ``reissue_time``, although it is not explicitly prevented.
       Optional.

    ``path``

       Default: ``/``. The path for which the auth_tkt cookie is valid.
       May be desirable if the application only serves part of a domain.
       Optional.

    ``http_only``

       Default: ``False``. Hide cookie from JavaScript by setting the
       HttpOnly flag. Not honored by all browsers.
       Optional.

    ``wild_domain``

       Default: ``True``. An auth_tkt cookie will be generated for the
       wildcard domain.
       Optional.

    ``debug``

        Default: ``False``.  If ``debug`` is ``True``, log messages to the
        Pyramid debug logger about the results of various authentication
        steps.  The output from debugging is useful for reporting to maillist
        or IRC channels when asking for support.

    ``hashalg``

       Default: ``sha512`` (the literal string).

       Any hash algorithm supported by Python's ``hashlib.new()`` function
       can be used as the ``hashalg``.

       Cookies generated by different instances of AuthTktAuthenticationPolicy
       using different ``hashalg`` options are not compatible. Switching the
       ``hashalg`` will imply that all existing users with a valid cookie will
       be required to re-login.

    Objects of this class implement the interface described by
    :class:`pyramid.interfaces.IAuthenticationPolicy`.
    """
    def __init__(self,
                 secret,
                 cookie_name='auth_tkt',
                 secure=False,
                 include_ip=False,
                 timeout=None,
                 reissue_time=None,
                 max_age=None,
                 path="/",
                 http_only=False,
                 wild_domain=True,
                 hashalg='sha512',
                 ):
        if hashalg == 'md5': #pragma NO COVER
            warnings.warn(
                'The MD5 hash function is known to be '
                'susceptible to collision attacks.  We recommend that '
                'you use the SHA512 algorithm instead for improved security.',
                DeprecationWarning,
                stacklevel=2
                )
        self.cookie = AuthTktCookieHelper(
            secret,
            cookie_name=cookie_name,
            secure=secure,
            include_ip=include_ip,
            timeout=timeout,
            reissue_time=reissue_time,
            max_age=max_age,
            http_only=http_only,
            path=path,
            wild_domain=wild_domain,
            hashalg=hashalg,
            )

    def unauthenticated_userid(self, request):
        """ See IAuthenticationPolicy.
        """
        result = self.cookie.identify(request)
        if result:
            userid = result['userid']
            if isinstance(userid, str) and userid.startswith('persona:'):
                userid = userid[len('persona:'):]
            return userid

    def authenticated_userid(self, request):
        """ See IAuthenticationPolicy.
        """
        context = request.context
        userid = self.unauthenticated_userid(request)
        if userid is None:
            return None

        if userid in (Authenticated, Everyone): #pragma NO COVER
            return None

        adapter = request.registry.queryMultiAdapter(
            (context, request), IUserLocator)
        if adapter is None:
            adapter = DefaultUserLocator(context, request)
        try:
            user = adapter.get_user_by_userid(userid)
        except ValueError: #pragma NO COVER
            user = None

        if user is not None:
            return userid

    def effective_principals(self, request):
        """ See IAuthenticationPolicy.
        """
        context = request.context
        effective_principals = [Everyone]
        userid = self.unauthenticated_userid(request)

        if userid is None:
            return effective_principals

        if userid in (Authenticated, Everyone): #pragma NO COVER
            return None

        effective_principals.append(userid)
        effective_principals.append('system.Identified')

        adapter = request.registry.queryMultiAdapter(
            (context, request), IUserLocator)
        if adapter is None:
            adapter = DefaultUserLocator(context, request)
        try:
            user = adapter.get_user_by_userid(userid)
        except ValueError:
            user = None
 
        if user is not None:
            effective_principals.append(Authenticated)
            effective_principals.extend(
                adapter.get_groupids(userid))

        return effective_principals

    def remember(self, request, principal, **kw):
        """ See IAuthenticationPolicy.
        """
        return self.cookie.remember(request, principal, **kw)

    def forget(self, request):
        """ See IAuthenticationPolicy.
        """
        return self.cookie.forget(request)
