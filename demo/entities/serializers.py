from smartmodels.drf.serializers import ResourceSerializer
from .models import Entity, Post, Question, Answer, Comment


class AbstractEntitySerializer(ResourceSerializer):
    class Meta:
        model = Entity
        abstract = True


class PostSerializer(AbstractEntitySerializer):
    class Meta:
        fields = '__all__'
        model = Post


class QuestionSerializer(AbstractEntitySerializer):
    class Meta:
        model = Question


class AnswerSerializer(AbstractEntitySerializer):
    class Meta:
        model = Answer


class CommentSerializer(AbstractEntitySerializer):
    class Meta:
        model = Comment