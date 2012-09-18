import json
import os
import tempfile
import unittest

from nose.tools import ok_, eq_

from standup import app
from standup.app import User, Project, Status, format_update, TAG_TMPL
from standup import settings
from standup.tests import status, user

class AppTestCase(unittest.TestCase):

    def setUp(self):
        self.db_fd, app.app.config['DATABASE'] = tempfile.mkstemp()
        app.app.config['SQLALCHEMY_DATABASE_URI'] = ('sqlite:///%s' %
            app.app.config['DATABASE'])
        app.app.config['TESTING'] = True
        self.app = app.app.test_client()
        app.db.create_all()

    def tearDown(self):
        app.db.session.remove()
        os.close(self.db_fd)
        os.unlink(app.app.config['DATABASE'])

    def test_create_first_status(self):
        """Test creating the very first status for a project and user."""
        data = json.dumps({
            'api_key': settings.API_KEY,
            'user': 'r1cky',
            'project': 'sumodev',
            'content': 'bug 123456'})
        response = self.app.post(
            '/api/v1/status/', data=data, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        assert 'bug 123456' in response.data

        # Verify the user was created.
        self.assertEqual(User.query.first().username, 'r1cky')
        # Verify the project was created.
        self.assertEqual(Project.query.first().slug, 'sumodev')
        # Verify the status was created.
        self.assertEqual(Status.query.first().content, 'bug 123456')

    def test_format_update(self):
        p = Project(name='mdndev', slug='mdndev',
                    repo_url='https://github.com/mozilla/kuma')
        app.db.session.add(p)
        app.db.session.commit()
        content = "#merge pull #1 and pR 2 to fix bug #3 and BUg 4"
        formatted_update = format_update(content, project=p)
        ok_('tag-merge' in formatted_update)
        ok_('pull/1' in formatted_update)
        ok_('pull/2' in formatted_update)
        ok_('show_bug.cgi?id=3' in formatted_update)
        ok_('show_bug.cgi?id=4' in formatted_update)

    def test_create_status_validation(self):
        """Verify validation of required fields."""
        # Missing user
        data = json.dumps({
            'api_key': settings.API_KEY,
            'project': 'sumodev',
            'content': 'bug 123456'})
        response = self.app.post(
            '/api/v1/status/', data=data, content_type='application/json')
        self.assertEqual(response.status_code, 400)

        # Missing project
        data = json.dumps({
            'api_key': settings.API_KEY,
            'user': 'r1cky',
            'content': 'bug 123456'})
        response = self.app.post(
            '/api/v1/status/', data=data, content_type='application/json')
        self.assertEqual(response.status_code, 400)

        # Missing content
        data = json.dumps({
            'api_key': settings.API_KEY,
            'user': 'r1cky',
            'project': 'sumodev'})
        response = self.app.post(
            '/api/v1/status/', data=data, content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_create_status_invalid_api_key(self):
        """Request with invalid API key should return 403."""
        data = json.dumps({
            'api_key': settings.API_KEY + '123',
            'user': 'r1cky',
            'project': 'sumodev',
            'content': 'bug 123456'})
        response = self.app.post(
            '/api/v1/status/', data=data, content_type='application/json')
        self.assertEqual(response.status_code, 403)

    def test_create_status_missing_api_key(self):
        """Request without an API key should return 403."""
        data = json.dumps({
            'user': 'r1cky',
            'project': 'sumodev',
            'content': 'bug 123456'})
        response = self.app.post(
            '/api/v1/status/', data=data, content_type='application/json')
        self.assertEqual(response.status_code, 403)

    def test_delete_status(self):
        """Test deletion of a status"""
        s = status(save=True)
        id = s.id

        data = json.dumps({
            'api_key': settings.API_KEY,
            'user': s.user.username})
        response = self.app.delete(
            '/api/v1/status/%s/' % s.id, data=data,
            content_type='application/json')
        self.assertEqual(response.status_code, 200)

        # Verify the status was deleted
        self.assertEqual(Status.query.get(id), None)

    def test_delete_status_validation(self):
        """Verify validation of required fields"""
        s = status(save=True)

        # Missing user
        data = json.dumps({'api_key': settings.API_KEY})
        response = self.app.delete(
            '/api/v1/status/%s/' % s.id, data=data,
            content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_delete_status_unauthorized(self):
        """Test that only user who created the status can delete it"""
        s = status(save=True)
        data = json.dumps({
            'api_key': settings.API_KEY,
            'user': s.user.username + '123'})
        response = self.app.delete(
            '/api/v1/status/%s/' % s.id, data=data,
            content_type='application/json')
        self.assertEqual(response.status_code, 403)

    def test_delete_status_invalid_api_key(self):
        """Request with invalid API key should return 403"""
        s = status(save=True)
        data = json.dumps({
            'api_key': settings.API_KEY + '123',
            'user': s.user.username})
        response = self.app.delete(
            '/api/v1/status/%s/' % s.id, data=data,
            content_type='application/json')
        self.assertEqual(response.status_code, 403)

    def test_delete_status_missing_api_key(self):
        """Request with missing API key should return 403"""
        s = status(save=True)
        data = json.dumps({'user': s.user.username})
        response = self.app.delete(
            '/api/v1/status/%s/' % s.id, data=data,
            content_type='application/json')
        self.assertEqual(response.status_code, 403)

    def test_update_user(self):
        """Test that a user can update their own settings"""
        u = user(save=True)
        id = u.id

        data = json.dumps({
            'api_key': settings.API_KEY,
            'user': u.username,
            'email': 'test@test.com',
            'github_handle': 'test',
            'name': 'Test'})
        response = self.app.post(
            '/api/v1/user/%s/' % u.id, data=data,
            content_type='application/json')
        self.assertEqual(response.status_code, 200)

        u = User.query.get(id)

        self.assertEqual(u.email, 'test@test.com')
        self.assertEqual(u.github_handle, 'test')
        self.assertEqual(u.name, 'Test')

    def test_update_user_by_admins(self):
        """Test that an admin can update another users settings and non-admins
        cannot update other users settings
        """
        u = user(save=True)
        a = user(username='admin', slug='admin', email='admin@mail.com',
                 is_admin=True, save=True)

        uid = u.id
        aid = a.id
        username = u.username

        data = json.dumps({
            'api_key': settings.API_KEY,
            'user': a.username,
            'email': 'test@test.com',
            'github_handle': 'test',
            'name': 'Test'})
        response = self.app.post(
            '/api/v1/user/%s/' % uid, data=data,
            content_type='application/json')
        self.assertEqual(response.status_code, 200)

        u = User.query.get(uid)

        self.assertEqual(u.email, 'test@test.com')
        self.assertEqual(u.github_handle, 'test')
        self.assertEqual(u.name, 'Test')

        data = json.dumps({
            'api_key': settings.API_KEY,
            'user': username,
            'email': 'test@test.com'})
        response = self.app.post(
            '/api/v1/user/%s/' % aid, data=data,
            content_type='application/json')
        self.assertEqual(response.status_code, 403)

    def test_update_user_validation(self):
        """Verify validation of required fields"""
        u = user(save=True)

        # Missing user
        data = json.dumps({'api_key': settings.API_KEY})
        response = self.app.post(
            '/api/v1/user/%s/' % u.id, data=data,
            content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_update_user_invalid_api_key(self):
        """Request with invalid API key should return 403"""
        u = user(save=True)
        data = json.dumps({
            'api_key': settings.API_KEY + '123',
            'user': u.username})
        response = self.app.post(
            '/api/v1/user/%s/' % u.id, data=data,
            content_type='application/json')
        self.assertEqual(response.status_code, 403)


    def test_udate_user_invalid_api_key(self):
        """Request with invalid API key should return 403"""
        u = user(save=True)
        data = json.dumps({'user': u.username})
        response = self.app.post(
            '/api/v1/user/%s/' % u.id, data=data,
            content_type='application/json')
        self.assertEqual(response.status_code, 403)


class FormatUpdateTest(unittest.TestCase):
    def test_tags(self):
        # Test valid tags.
        for tag in ('#t', '#tag', '#TAG', '#tag123'):
            expected = '%s %s' % (TAG_TMPL.format('', tag[1:]), tag)
            eq_(format_update(tag), expected)

        # Test invalid tags.
        for tag in ('#1', '#.abc', '#?abc'):
            eq_(format_update(tag), tag)
