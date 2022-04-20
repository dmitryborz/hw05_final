from django.contrib.auth import get_user_model
from django.test import TestCase
from django.conf import settings

from ..models import Group, Post

User = get_user_model()


class GroupModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )

    def test_group_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        group = GroupModelTest.group
        expected_title = group.title
        self.assertEqual(expected_title, str(group.title))


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая пост Тестовая пост Тестовая пост Тестовая пост',
        )

    def test_post_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        post = PostModelTest.post
        expected_object_name = post.text[:settings.TEST_LEN_TEXT]
        self.assertEqual(expected_object_name, str(post))

    def test_text_verbose_name(self):
        """verbose_name поля text совпадает с ожидаемым."""
        post = PostModelTest.post
        verbose = post._meta.get_field('text').verbose_name
        self.assertEqual(verbose, 'Текст')
