"""
Unit tests for the Deis api app.

Run the tests with "./manage.py test api"
"""


import json

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.authtoken.models import Token

from api.models import Domain


class DomainTest(TestCase):

    """Tests creation of domains"""

    fixtures = ['tests.json']

    def setUp(self):
        self.user = User.objects.get(username='autotest')
        self.token = Token.objects.get(user=self.user).key
        url = '/v2/apps'
        response = self.client.post(url, HTTP_AUTHORIZATION='token {}'.format(self.token))
        self.assertEqual(response.status_code, 201)
        self.app_id = response.data['id']  # noqa

    def test_response_data(self):
        """Test that the serialized response contains only relevant data."""
        response = self.client.post(
            '/v2/apps',
            json.dumps({'id': 'test'}),
            content_type='application/json',
            HTTP_AUTHORIZATION='token {}'.format(self.token)
        )

        response = self.client.post(
            '/v2/apps/test/domains',
            json.dumps({'domain': 'test-domain.example.com'}),
            content_type='application/json',
            HTTP_AUTHORIZATION='token {}'.format(self.token)
        )

        for key in response.data:
            self.assertIn(key, ['uuid', 'owner', 'created', 'updated', 'app', 'domain'])

        expected = {
            'owner': self.user.username,
            'app': 'test',
            'domain': 'test-domain.example.com'
        }
        self.assertDictContainsSubset(expected, response.data)

    def test_manage_domain(self):
        url = '/v2/apps/{app_id}/domains'.format(app_id=self.app_id)
        test_domains = [
            'test-domain.example.com',
            'django.paas-sandbox',
            'domain',
            'not.too.loooooooooooooooooooooooooooooooooooooooooooooooooooooooooooong',
            '3com.com',
            'w3.example.com',
            'MYDOMAIN.NET',
            'autotest.127.0.0.1.xip.io',
            '*.deis.example.com',
        ]

        for domain in test_domains:
            msg = "failed on \"{}\"".format(domain)

            # Create
            response = self.client.post(
                url,
                json.dumps({'domain': domain}),
                content_type='application/json',
                HTTP_AUTHORIZATION='token {}'.format(self.token)
            )
            self.assertEqual(response.status_code, 201, msg)

            # Fetch
            url = '/v2/apps/{app_id}/domains'.format(app_id=self.app_id)
            response = self.client.get(
                url,
                content_type='application/json',
                HTTP_AUTHORIZATION='token {}'.format(self.token)
            )
            expected = [data['domain'] for data in response.data['results']]
            self.assertEqual([self.app_id, domain], expected, msg)

            # Delete
            url = '/v2/apps/{app_id}/domains/{hostname}'.format(hostname=domain,
                                                                app_id=self.app_id)
            response = self.client.delete(
                url,
                content_type='application/json',
                HTTP_AUTHORIZATION='token {}'.format(self.token)
            )
            self.assertEqual(response.status_code, 204, msg)

            # Verify removal
            url = '/v2/apps/{app_id}/domains'.format(app_id=self.app_id)
            response = self.client.get(
                url,
                content_type='application/json',
                HTTP_AUTHORIZATION='token {}'.format(self.token)
            )
            self.assertEqual(1, response.data['count'], msg)

            # verify only app domain is left
            expected = [data['domain'] for data in response.data['results']]
            self.assertEqual([self.app_id], expected, msg)

    def test_delete_domain_does_not_exist(self):
        """Remove a domain that does not exist"""
        url = '/v2/apps/{app_id}/domains'.format(app_id=self.app_id)

        url = '/v2/apps/{app_id}/domains/{domain}'.format(domain='test-domain.example.com',
                                                          app_id=self.app_id)
        response = self.client.delete(url, content_type='application/json',
                                      HTTP_AUTHORIZATION='token {}'.format(self.token))
        self.assertEqual(response.status_code, 404)

    def test_delete_domain_does_not_remove_latest(self):
        """https://github.com/deis/deis/issues/3239"""
        url = '/v2/apps/{app_id}/domains'.format(app_id=self.app_id)
        test_domains = [
            'test-domain.example.com',
            'django.paas-sandbox',
        ]
        for domain in test_domains:
            response = self.client.post(
                url,
                json.dumps({'domain': domain}),
                content_type='application/json',
                HTTP_AUTHORIZATION='token {}'.format(self.token)
            )
            self.assertEqual(response.status_code, 201)

        url = '/v2/apps/{app_id}/domains/{domain}'.format(domain=test_domains[0],
                                                          app_id=self.app_id)
        response = self.client.delete(url, content_type='application/json',
                                      HTTP_AUTHORIZATION='token {}'.format(self.token))
        self.assertEqual(response.status_code, 204)
        with self.assertRaises(Domain.DoesNotExist):
            Domain.objects.get(domain=test_domains[0])

    def test_delete_domain_does_not_remove_others(self):
        """https://github.com/deis/deis/issues/3475"""
        self.test_delete_domain_does_not_remove_latest()
        self.assertEqual(Domain.objects.all().count(), 2)

    def test_manage_domain_invalid_app(self):
        # Create domain
        url = '/v2/apps/{app_id}/domains'.format(app_id="this-app-does-not-exist")
        response = self.client.post(
            url,
            json.dumps({'domain': 'test-domain.example.com'}),
            content_type='application/json',
            HTTP_AUTHORIZATION='token {}'.format(self.token)
        )
        self.assertEqual(response.status_code, 404)

        # verify
        url = '/v2/apps/{app_id}/domains'.format(app_id='this-app-does-not-exist')
        response = self.client.get(
            url,
            content_type='application/json',
            HTTP_AUTHORIZATION='token {}'.format(self.token)
        )
        self.assertEqual(response.status_code, 404)

    def test_manage_domain_invalid_domain(self):
        url = '/v2/apps/{app_id}/domains'.format(app_id=self.app_id)
        test_domains = [
            'this_is_an.invalid.domain',
            'this-is-an.invalid.1',
            'django.pass--sandbox',
            'domain1',
            '3333.com',
            'too.looooooooooooooooooooooooooooooooooooooooooooooooooooooooooooong',
            'foo.*.bar.com',
            '*',
        ]
        for domain in test_domains:
            msg = "failed on \"{}\"".format(domain)

            response = self.client.post(
                url,
                json.dumps({'domain': domain}),
                content_type='application/json',
                HTTP_AUTHORIZATION='token {}'.format(self.token)
            )
            self.assertEqual(response.status_code, 400, msg)

    def test_admin_can_add_domains_to_other_apps(self):
        """If a non-admin user creates an app, an administrator should be able to add
        domains to it.
        """
        user = User.objects.get(username='autotest2')
        token = Token.objects.get(user=user).key
        url = '/v2/apps'
        response = self.client.post(url, HTTP_AUTHORIZATION='token {}'.format(token))
        self.assertEqual(response.status_code, 201)

        url = '/v2/apps/{}/domains'.format(self.app_id)
        response = self.client.post(
            url,
            json.dumps({'domain': 'example.deis.example.com'}),
            content_type='application/json',
            HTTP_AUTHORIZATION='token {}'.format(self.token)
        )
        self.assertEqual(response.status_code, 201)

    def test_unauthorized_user_cannot_modify_domain(self):
        """
        An unauthorized user should not be able to modify other domains.

        Since an unauthorized user should not know about the application at all, these
        requests should return a 404.
        """
        app_id = 'autotest'
        url = '/v2/apps'
        response = self.client.post(
            url,
            json.dumps({'id': app_id}),
            content_type='application/json',
            HTTP_AUTHORIZATION='token {}'.format(self.token)
        )

        unauthorized_user = User.objects.get(username='autotest2')
        unauthorized_token = Token.objects.get(user=unauthorized_user).key
        url = '{}/{}/domains'.format(url, app_id)
        response = self.client.post(
            url,
            json.dumps({'domain': 'example.com'}),
            content_type='application/json',
            HTTP_AUTHORIZATION='token {}'.format(unauthorized_token)
        )
        self.assertEqual(response.status_code, 403)
