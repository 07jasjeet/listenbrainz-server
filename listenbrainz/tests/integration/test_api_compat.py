""" This module tests Last.fm Scrobbling 2.0 compatibility features """

# listenbrainz-server - Server for the ListenBrainz project.
#
# Copyright (C) 2018 Kartikeya Sharma <09kartikeya@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
import json
import logging
import time

import xmltodict
from flask import url_for

import listenbrainz.db.user as db_user
from listenbrainz.db.lastfm_session import Session
from listenbrainz.db.lastfm_token import Token
from listenbrainz.db.lastfm_user import User
from listenbrainz.listenstore.timescale_utils import recalculate_all_user_data
from listenbrainz.tests.integration import ListenAPIIntegrationTestCase
from listenbrainz.webserver import timescale_connection


class APICompatTestCase(ListenAPIIntegrationTestCase):

    def setUp(self):
        super(APICompatTestCase, self).setUp()
        self.lb_user = db_user.get_or_create(self.conn, 1, 'apicompattestuser')
        self.lfm_user = User(
            self.lb_user['id'],
            self.lb_user['created'],
            self.lb_user['musicbrainz_id'],
            self.lb_user['auth_token'],
        )
        self.log = logging.getLogger(__name__)
        self.ls = timescale_connection._ts

    def test_complete_workflow_json(self):
        """ Integration test for complete workflow to submit a listen using Last.fm compat api """
        data = {
            'method': 'auth.gettoken',
            'api_key': self.lfm_user.api_key,
            'format': 'json',
        }
        r = self.client.post(url_for('api_compat.api_methods'), data=data)
        self.assert200(r)
        token = r.json['token']

        # login as user
        with self.client.session_transaction() as session:
            session['_user_id'] = self.lb_user['login_id']
            session['_fresh'] = True

        r = self.client.post(
            url_for('api_compat.api_auth_approve'),
            data=f"token={token}",
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        self.assert200(r)

        data = {
            'method': 'auth.getsession',
            'api_key': self.lfm_user.api_key,
            'token': token,
            'format': 'json'
        }
        r = self.client.post(url_for('api_compat.api_methods'), data=data)
        self.assert200(r)
        sk = r.json['session']['key']

        data = {
            'method': 'track.scrobble',
            'api_key': self.lfm_user.api_key,
            'sk': sk,
            'format': 'json',
            'artist[0]': 'Kishore Kumar',
            'track[0]': 'Saamne Ye Kaun Aya',
            'album[0]': 'Jawani Diwani',
            'duration[0]': 300,
            'timestamp[0]': int(time.time()),
        }
        r = self.client.post(url_for('api_compat.api_methods'), data=data)
        self.assert200(r)

        expected = {
            "scrobbles": {
                "scrobble": {
                    "track": {
                        "#text": data["track[0]"],
                        "corrected": "0"
                    },
                    "artist": {
                        "#text": data["artist[0]"],
                        "corrected": "0"
                    },
                    "album": {
                        "#text": data["album[0]"],
                        "corrected": "0"
                    },
                    "albumArtist": {
                        "#text": data["artist[0]"],
                        "corrected": "0"
                    },
                    "timestamp": str(data["timestamp[0]"]),
                    "ignoredMessage": {
                        "code": "0"
                    }
                },
                "accepted": "1",
                "ignored": "0"
            }
        }
        self.assertEqual(expected, r.json)

        # Check if listen reached the timescale listenstore
        time.sleep(1)
        recalculate_all_user_data(self.conn, self.ts_conn)
        listens, _, _ = self.ls.fetch_listens(self.ts_conn, self.lb_user, from_ts=data["timestamp[0]"]-1)
        self.assertEqual(len(listens), 1)

    def test_record_listen_now_playing(self):
        """ Tests if listen of type 'nowplaying' is recorded correctly
            if valid information is provided.
        """

        token = Token.generate(self.conn, self.lfm_user.api_key)
        token.approve(self.lfm_user.name)
        session = Session.create(self.conn, token)

        data = {
            'method': 'track.updateNowPlaying',
            'api_key': self.lfm_user.api_key,
            'sk': session.sid,
            'artist[0]': 'Kishore Kumar',
            'track[0]': 'Saamne Ye Kaun Aya',
            'album[0]': 'Jawani Diwani',
            'duration[0]': 300,
            'timestamp[0]': int(time.time()),
        }

        r = self.client.post(url_for('api_compat.api_methods'), data=data)
        self.assert200(r)

        response = xmltodict.parse(r.data)
        self.assertEqual(response['lfm']['@status'], 'ok')
        self.assertIsNotNone(response['lfm']['nowplaying'])

    def test_get_token(self):
        """ Tests if the token generated by get_token method is valid. """

        data = {
            'method': 'auth.gettoken',
            'api_key': self.lfm_user.api_key,
        }

        r = self.client.post(url_for('api_compat.api_methods'), data=data)
        self.assert200(r)

        response = xmltodict.parse(r.data)
        self.assertEqual(response['lfm']['@status'], 'ok')

        token = Token.load(response['lfm']['token'], api_key=self.lfm_user.api_key)
        self.assertIsNotNone(token)

    def test_get_session(self):
        """ Tests if the session key is valid and session is established correctly. """

        token = Token.generate(self.conn, self.lfm_user.api_key)
        token.approve(self.lfm_user.name)

        data = {
            'method': 'auth.getsession',
            'api_key': self.lfm_user.api_key,
            'token': token.token,
        }
        r = self.client.post(url_for('api_compat.api_methods'), data=data)
        self.assert200(r)
        self.assertEqual(r.headers["Content-type"], "application/xml; charset=utf-8")

        response = xmltodict.parse(r.data)
        self.assertEqual(response['lfm']['@status'], 'ok')
        self.assertEqual(response['lfm']['session']['name'], self.lfm_user.name)

        session_key = Session.load(response['lfm']['session']['key'])
        self.assertIsNotNone(session_key)

    def test_get_session_invalid_token(self):
        """ Tests if correct error codes are returned in case token supplied
            is invalid during establishment of session.
        """

        data = {
            'method': 'auth.getsession',
            'api_key': self.lfm_user.api_key,
            'token': '',
        }
        r = self.client.post(url_for('api_compat.api_methods'), data=data)
        self.assert200(r)
        self.assertEqual(r.headers["Content-type"], "application/xml; charset=utf-8")

        response = xmltodict.parse(r.data)
        self.assertEqual(response['lfm']['@status'], 'failed')
        self.assertEqual(response['lfm']['error']['@code'], '4')

    def test_user_getinfo_no_listenstore(self):
        """If this listenstore is unavailable, performing a query that gets user information
           (touches the listenstore for user count) should return an error message in the
           requested format"""
        timescale_connection._ts = None

        token = Token.generate(self.conn, self.lfm_user.api_key)
        token.approve(self.lfm_user.name)
        session = Session.create(self.conn, token)

        data = {
            'method': 'user.getInfo',
            'api_key': self.lfm_user.api_key,
            'sk': session.sid
        }

        r = self.client.post(url_for('api_compat.api_methods'), data=data)
        self.assert200(r)
        self.assertEqual(r.headers["Content-type"], "application/xml; charset=utf-8")

        expected_message = b"""<?xml version="1.0" encoding="utf-8"?>
<lfm status="failed">
  <error code="16">The service is temporarily unavailable, please try again.</error>
</lfm>"""
        assert r.data == expected_message

    def test_record_listen(self):
        """ Tests if listen is recorded correctly if valid information is provided. """

        token = Token.generate(self.conn, self.lfm_user.api_key)
        token.approve(self.lfm_user.name)
        session = Session.create(self.conn, token)

        timestamp = int(time.time())
        data = {
            'method': 'track.scrobble',
            'api_key': self.lfm_user.api_key,
            'sk': session.sid,
            'artist[0]': 'Kishore Kumar',
            'track[0]': 'Saamne Ye Kaun Aya',
            'album[0]': 'Jawani Diwani',
            'duration[0]': 300,
            'timestamp[0]': timestamp,
        }

        r = self.client.post(url_for('api_compat.api_methods'), data=data)
        self.assert200(r)
        self.assertEqual(r.headers["Content-type"], "application/xml; charset=utf-8")

        response = xmltodict.parse(r.data)
        self.assertEqual(response['lfm']['@status'], 'ok')
        self.assertEqual(response['lfm']['scrobbles']['@accepted'], '1')

        # Check if listen reached the timescale listenstore
        time.sleep(1)
        recalculate_all_user_data(self.conn, self.ts_conn)
        listens, _, _ = self.ls.fetch_listens(self.conn, self.lb_user, from_ts=timestamp-1)
        self.assertEqual(len(listens), 1)

    def test_record_invalid_listen(self):
        """ Tests that error is raised if submited data contains unicode null """
        token = Token.generate(self.conn, self.lfm_user.api_key)
        token.approve(self.lfm_user.name)
        session = Session.create(self.conn, token)

        timestamp = int(time.time())
        data = {
            'method': 'track.scrobble',
            'api_key': self.lfm_user.api_key,
            'sk': session.sid,
            'artist[0]': '\u0000Kishore Kumar',
            'track[0]': 'Saamne Ye Kaun Aya',
            'album[0]': 'Jawani Diwani',
            'duration[0]': 300,
            'timestamp[0]': timestamp,
        }

        r = self.client.post(url_for('api_compat.api_methods'), data=data)
        self.assert400(r)
        self.assertEqual(r.json["error"], "\u0000Kishore Kumar contains a unicode null")

    def test_record_listen_multiple_listens(self):
        """ Tests if multiple listens get recorded correctly in case valid information
            is provided.
        """

        token = Token.generate(self.conn, self.lfm_user.api_key)
        token.approve(self.lfm_user.name)
        session = Session.create(self.conn, token)

        timestamp = int(time.time())
        data = {
            'method': 'track.scrobble',
            'api_key': self.lfm_user.api_key,
            'sk': session.sid,
            'artist[0]': 'Kishore Kumar',
            'track[0]': 'Saamne Ye Kaun Aya',
            'album[0]': 'Jawani Diwani',
            'duration[0]': 300,
            'timestamp[0]': timestamp,
            'artist[1]': 'Fifth Harmony',
            'track[1]': 'Deliver',
            'duration[1]': 200,
            'timestamp[1]': timestamp+300,
        }

        r = self.client.post(url_for('api_compat.api_methods'), data=data)
        self.assert200(r)

        response = xmltodict.parse(r.data)
        self.assertEqual(response['lfm']['@status'], 'ok')
        self.assertEqual(response['lfm']['scrobbles']['@accepted'], '2')

        # Check if listens reached the timescale listenstore
        time.sleep(1)
        recalculate_all_user_data(self.conn, self.ts_conn)
        listens, _, _ = self.ls.fetch_listens(self.ts_conn, self.lb_user, from_ts=timestamp-1)
        self.assertEqual(len(listens), 2)

    def test_create_response_for_single_listen(self):
        """ Tests create_response_for_single_listen method in api_compat
            to check if responses are generated correctly.
        """

        from listenbrainz.webserver.views.api_compat import create_response_for_single_listen

        timestamp = int(time.time())

        original_listen = {
            'artist': 'Kishore Kumar',
            'track': 'Saamne Ye Kaun Aya',
            'album': 'Jawani Diwani',
            'duration': 300,
            'timestamp': timestamp,
        }

        augmented_listen = {
            'listened_at': timestamp,
            'track_metadata': {
                'artist_name': 'Kishore Kumar',
                'track_name':  'Saamne Ye Kaun Aya',
                'release_name': 'Jawani Diwani',
                'additional_info': {
                    'track_length': 300
                }
            }
        }

        # If original listen and augmented listen are same
        xml_response = create_response_for_single_listen(original_listen, augmented_listen, listen_type="listens")
        response = xmltodict.parse(xml_response)

        self.assertEqual(response['scrobble']['track']['#text'], 'Saamne Ye Kaun Aya')
        self.assertEqual(response['scrobble']['track']['@corrected'], '0')
        self.assertEqual(response['scrobble']['artist']['#text'], 'Kishore Kumar')
        self.assertEqual(response['scrobble']['artist']['@corrected'], '0')
        self.assertEqual(response['scrobble']['album']['#text'], 'Jawani Diwani')
        self.assertEqual(response['scrobble']['timestamp'], str(timestamp))

        # If listen type is 'playing_now'
        xml_response = create_response_for_single_listen(original_listen, augmented_listen, listen_type="playing_now")
        response = xmltodict.parse(xml_response)

        self.assertEqual(response['nowplaying']['track']['#text'], 'Saamne Ye Kaun Aya')
        self.assertEqual(response['nowplaying']['track']['@corrected'], '0')
        self.assertEqual(response['nowplaying']['artist']['#text'], 'Kishore Kumar')
        self.assertEqual(response['nowplaying']['artist']['@corrected'], '0')
        self.assertEqual(response['nowplaying']['album']['#text'], 'Jawani Diwani')
        self.assertEqual(response['nowplaying']['album']['@corrected'], '0')
        self.assertEqual(response['nowplaying']['timestamp'], str(timestamp))

        # If artist was corrected
        original_listen['artist'] = 'Pink'

        xml_response = create_response_for_single_listen(original_listen, augmented_listen, listen_type="listens")
        response = xmltodict.parse(xml_response)

        self.assertEqual(response['scrobble']['track']['#text'], 'Saamne Ye Kaun Aya')
        self.assertEqual(response['scrobble']['track']['@corrected'], '0')
        self.assertEqual(response['scrobble']['artist']['#text'], 'Kishore Kumar')
        self.assertEqual(response['scrobble']['artist']['@corrected'], '1')
        self.assertEqual(response['scrobble']['album']['#text'], 'Jawani Diwani')
        self.assertEqual(response['scrobble']['album']['@corrected'], '0')
        self.assertEqual(response['scrobble']['timestamp'], str(timestamp))

        # If track was corrected
        original_listen['artist'] = 'Kishore Kumar'
        original_listen['track'] = 'Deliver'

        xml_response = create_response_for_single_listen(original_listen, augmented_listen, listen_type="listens")
        response = xmltodict.parse(xml_response)

        self.assertEqual(response['scrobble']['track']['#text'], 'Saamne Ye Kaun Aya')
        self.assertEqual(response['scrobble']['track']['@corrected'], '1')
        self.assertEqual(response['scrobble']['artist']['#text'], 'Kishore Kumar')
        self.assertEqual(response['scrobble']['artist']['@corrected'], '0')
        self.assertEqual(response['scrobble']['album']['#text'], 'Jawani Diwani')
        self.assertEqual(response['scrobble']['album']['@corrected'], '0')
        self.assertEqual(response['scrobble']['timestamp'], str(timestamp))

        # If album was corrected
        original_listen['track'] = 'Saamne Ye Kaun Aya'
        original_listen['album'] = 'Good Life'

        xml_response = create_response_for_single_listen(original_listen, augmented_listen, listen_type="listens")
        response = xmltodict.parse(xml_response)

        self.assertEqual(response['scrobble']['track']['#text'], 'Saamne Ye Kaun Aya')
        self.assertEqual(response['scrobble']['track']['@corrected'], '0')
        self.assertEqual(response['scrobble']['artist']['#text'], 'Kishore Kumar')
        self.assertEqual(response['scrobble']['artist']['@corrected'], '0')
        self.assertEqual(response['scrobble']['album']['#text'], 'Jawani Diwani')
        self.assertEqual(response['scrobble']['album']['@corrected'], '1')
        self.assertEqual(response['scrobble']['timestamp'], str(timestamp))
