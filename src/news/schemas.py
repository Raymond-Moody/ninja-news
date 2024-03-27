from ninja import ModelSchema
from .models import Video, Category, Channel

class VideoSchema(ModelSchema):
    class Meta:
        model = Video
        fields = ('id', 'url', 'title', 'transcript', 'channel', 'publication_date', 'category')

class CategorySchema(ModelSchema):
    class Meta:
        model = Category
        fields = ('id', 'name')

class ChannelSchema(ModelSchema):
    class Meta:
        model = Channel
        fields = ('id', 'name')
