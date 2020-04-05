#####################################################################################
#
#  Copyright (c) Crossbar.io Technologies GmbH
#
#  Unless a separate license agreement exists between you and Crossbar.io GmbH (e.g.
#  you have purchased a commercial license), the license terms below apply.
#
#  Should you enter into a separate license agreement after having received a copy of
#  this software, then the terms of such license agreement replace the terms below at
#  the time at which such license agreement becomes effective.
#
#  In case a separate license agreement ends, and such agreement ends without being
#  replaced by another separate license agreement, the license terms below apply
#  from the time at which said agreement ends.
#
#  LICENSE TERMS
#
#  This program is free software: you can redistribute it and/or modify it under the
#  terms of the GNU Affero General Public License, version 3, as published by the
#  Free Software Foundation. This program is distributed in the hope that it will be
#  useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
#  See the GNU Affero General Public License Version 3 for more details.
#
#  You should have received a copy of the GNU Affero General Public license along
#  with this program. If not, see <http://www.gnu.org/licenses/agpl-3.0.en.html>.
#
#####################################################################################

from autobahn import util
from autobahn.wamp import types

from txaio import make_logger

from crossbar.router.auth.pending import PendingAuth

__all__ = ('PendingAuthAnonymous',)


class PendingAuthAnonymous(PendingAuth):

    """
    Pending authentication information for WAMP-Anonymous authentication.
    """

    log = make_logger()

    AUTHMETHOD = 'anonymous'

    def hello(self, realm, details):

        # remember the realm the client requested to join (if any)
        self._realm = realm

        self._authid = self._config.get('authid', util.generate_serial_number())

        self._session_details['authmethod'] = 'anonymous'
        self._session_details['authextra'] = details.authextra

        # WAMP-anonymous "static"
        if self._config['type'] == 'static':

            self._authprovider = 'static'

            # FIXME: if cookie tracking is enabled, set authid to cookie value
            # self._authid = self._transport._cbtid

            principal = {
                'authid': self._authid,
                'role': self._config.get('role', 'anonymous'),
                'extra': details.authextra
            }

            error = self._assign_principal(principal)
            if error:
                return error

            return self._accept()

        # WAMP-Ticket "dynamic"
        elif self._config['type'] == 'dynamic':

            self._authprovider = 'dynamic'

            error = self._init_dynamic_authenticator()
            if error:
                return error

            d = self._authenticator_session.call(self._authenticator, self._realm, self._authid, self._session_details)

            def on_authenticate_ok(principal):
                error = self._assign_principal(principal)
                if error:
                    return error

                return self._accept()

            def on_authenticate_error(err):
                return self._marshal_dynamic_authenticator_error(err)

            d.addCallbacks(on_authenticate_ok, on_authenticate_error)

            return d

        else:
            # should not arrive here, as config errors should be caught earlier
            return types.Deny(message='invalid authentication configuration (authentication type "{}" is unknown)'.format(self._config['type']))


class PendingAuthAnonymousProxy(PendingAuthAnonymous):
    """
    Pending Anonymous authentication with additions for proxy
    """

    log = make_logger()
    AUTHMETHOD = 'anonymous-proxy'

    def hello(self, realm, details):
        # now, check anything we got in the authextra
        extra = details.authextra or {}
        if extra.get('cb_proxy_authid', None):
            details.authid = extra['cb_proxy_authid']

        if extra.get('cb_proxy_authrole', None):
            details.authrole = extra['cb_proxy_authrole']

        if extra.get('cb_proxy_authrealm', None):
            realm = extra['cb_proxy_authrealm']

        return super(PendingAuthAnonymousProxy, self).hello(realm, details)
