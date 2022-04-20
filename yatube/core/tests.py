from http import HTTPStatus

from django.test import TestCase, Client


class ViewTestClass(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_error_page(self):
        response = self.guest_client.get('/nonexist-page/')
        self.assertTemplateUsed(response, 'core/404.html')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
