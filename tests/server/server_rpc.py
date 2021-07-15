#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/server/server_rpc.py
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are
#  met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following disclaimer
#    in the documentation and/or other materials provided with the
#    distribution.
#  * Neither the name of the project nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#  A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#  OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#  LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import types
import unittest

from king_phisher import errors
from king_phisher import startup
from king_phisher import version
from king_phisher.server import server_rpc
from king_phisher.testing import KingPhisherServerTestCase
from king_phisher.utilities import random_string

import advancedhttpserver

_certbot_bin_path = startup.which('certbot')

class ServerRPCTests(KingPhisherServerTestCase):
	def test_rpc_config_get(self):
		server_addresses = self.rpc('config/get', 'server.addresses')
		self.assertIsInstance(server_addresses, list)
		self.assertIsNotEmpty(server_addresses)
		self.assertEqual(server_addresses, self.config.get('server.addresses'))

		config_results = self.rpc('config/get', ['server.require_id', 'server.web_root'])
		self.assertIsInstance(config_results, dict)
		self.assertIn('server.require_id', config_results)
		self.assertEqual(config_results['server.require_id'], self.config.get('server.require_id'))
		self.assertIn('server.web_root', config_results)
		self.assertEqual(config_results['server.web_root'], self.config.get('server.web_root'))

	def test_rpc_config_get_permissions(self):
		self.assertTrue(self.config.has_option('server.database'))
		self.assertRPCPermissionDenied('config/get', 'server.database')

	def test_rpc_campaign_delete(self):
		campaign_name = random_string(10)
		campaign_id = self.rpc('campaign/new', campaign_name)
		self.rpc('db/table/delete', 'campaigns', campaign_id)

	def test_rpc_campaign_new(self):
		campaign_name = random_string(10)
		campaign_id = self.rpc('campaign/new', campaign_name)
		self.assertIsInstance(campaign_id, int)
		campaigns = self.rpc.remote_table('campaigns')
		self.assertIsInstance(campaigns, types.GeneratorType)
		campaigns = list(campaigns)
		self.assertEqual(len(campaigns), 1)
		campaign = campaigns[0]
		self.assertEqual(campaign.id, campaign_id)
		self.assertEqual(campaign.name, campaign_name)

	def test_rpc_config_set(self):
		config_key = server_rpc.CONFIG_WRITEABLE[0]
		config_value = random_string(10)
		self.rpc('config/set', {config_key: config_value})
		self.assertEqual(self.rpc('config/get', config_key), config_value)

	def test_rpc_config_set_permissions(self):
		config_key = random_string(10)
		config_value = random_string(10)
		self.assertRPCPermissionDenied('config/set', {config_key: config_value})

	def test_rpc_graphql(self):
		response = self.rpc('graphql', '{ version }')
		self.assertIn('data', response)
		self.assertIn('errors', response)
		self.assertIsNotNone(response['data'])
		self.assertIsNone(response['errors'])

		response = response['data'].get('version')
		self.assertEquals(response, version.version)

	def test_rpc_graphql_rpc_errors(self):
		bad_query = '{ foobar }'
		with self.assertRaises(errors.KingPhisherGraphQLQueryError) as context:
			self.rpc.graphql(bad_query)
		error = context.exception
		self.assertIsInstance(error.errors, list)
		self.assertIsNotEmpty(error.errors)
		self.assertIsInstance(error.query, str)
		self.assertEqual(error.query, bad_query)

	def test_rpc_graphql_raw_errors(self):
		response = self.rpc('graphql', '{ foobar }')
		self.assertIn('data', response)
		self.assertIn('errors', response)
		self.assertIsNone(response['data'])
		self.assertIsNotNone(response['errors'])

		self.assertIsNotEmpty(response['errors'])
		for error in response['errors']:
			self.assertIsInstance(error, str)

	def test_rpc_hostnames_get(self):
		hostnames = self.rpc('hostnames/get')
		self.assertIsInstance(hostnames, list)

	def test_rpc_hostnames_add(self):
		new_hostname = random_string(16) + '.local'
		self.rpc('hostnames/add', new_hostname)
		hostnames = self.rpc('hostnames/get')
		self.assertIsInstance(hostnames, list)
		self.assertIn(new_hostname, hostnames)

	def test_rpc_is_unauthorized(self):
		http_response = self.http_request('/ping', method='RPC')
		self.assertHTTPStatus(http_response, 401)

	@unittest.skipUnless(_certbot_bin_path, 'due to certbot being unavailable')
	def test_rpc_ssl_letsencrypt_certbot_version(self):
		version = self.rpc('ssl/letsencrypt/certbot_version')
		self.assertIsNotNone(version, 'the certbot version was not retrieved')
		self.assertRegexpMatches(version, r'(\d.)*\d', 'the certbot version is invalid')

	def test_rpc_ssl_sni_hostnames_get(self):
		sni_hostnames = self.rpc('ssl/sni_hostnames/get')
		self.assertIsInstance(sni_hostnames, dict)

	def test_rpc_ssl_sni_hostnames_load(self):
		fake_hostname = random_string(16)
		self.assertFalse(self.rpc('ssl/sni_hostnames/load', fake_hostname))

	def test_rpc_ssl_sni_hostnames_unload(self):
		fake_hostname = random_string(16)
		self.assertFalse(self.rpc('ssl/sni_hostnames/unload', fake_hostname))

	def test_rpc_ssl_status(self):
		ssl_status = self.rpc('ssl/status')
		self.assertIsInstance(ssl_status, dict)
		self.assertIn('enabled', ssl_status)
		self.assertIn('has-sni', ssl_status)
		self.assertEqual(ssl_status['has-sni'], advancedhttpserver.g_ssl_has_server_sni)

	def test_rpc_ping(self):
		self.assertTrue(self.rpc('ping'))

	def test_rpc_remote_table(self):
		self.test_rpc_campaign_new()
		campaign = list(self.rpc.remote_table('campaigns'))[0]
		campaign = campaign._asdict()
		self.assertIsInstance(campaign, dict)
		meta_table = self.server.tables_api['campaigns']
		self.assertEqual(sorted(campaign.keys()), sorted(meta_table.column_names))

	def test_rpc_shutdown(self):
		self.assertIsNone(self.rpc('shutdown'))
		self.shutdown_requested = True

	def test_rpc_table_count(self):
		self.assertEqual(self.rpc('db/table/count', 'campaigns'), 0)
		self.assertEqual(self.rpc('db/table/count', 'messages'), 0)
		self.assertEqual(self.rpc('db/table/count', 'visits'), 0)
		self.test_rpc_campaign_new()
		self.assertEqual(self.rpc('db/table/count', 'campaigns'), 1)

	def test_rpc_table_view(self):
		self.test_rpc_campaign_new()
		campaign = self.rpc('db/table/view', 'campaigns')
		self.assertTrue(bool(campaign))
		self.assertEqual(len(campaign['rows']), 1)
		meta_table = self.server.tables_api['campaigns']
		self.assertEqual(len(campaign['rows'][0]), len(meta_table.column_names))
		self.assertEqual(sorted(campaign['columns']), sorted(meta_table.column_names))

	def test_rpc_set_value(self):
		campaign_name = random_string(10)
		new_campaign_name = random_string(10)
		campaign_id = self.rpc('campaign/new', campaign_name)
		campaign = self.rpc.remote_table_row('campaigns', campaign_id)
		self.assertEqual(campaign.id, campaign_id)
		self.assertEqual(campaign.name, campaign_name)
		self.rpc('db/table/set', 'campaigns', campaign_id, 'name', new_campaign_name)
		campaign = self.rpc.remote_table_row('campaigns', campaign_id)
		self.assertEqual(campaign.name, new_campaign_name)

	def test_rpc_version(self):
		response = self.rpc('version')
		self.assertIn('version', response)
		self.assertIn('version_info', response)
		self.assertEqual(response['version'], version.version)
		self.assertEqual(response['version_info']['major'], version.version_info.major)
		self.assertEqual(response['version_info']['minor'], version.version_info.minor)
		self.assertEqual(response['version_info']['micro'], version.version_info.micro)

if __name__ == '__main__':
	unittest.main()
