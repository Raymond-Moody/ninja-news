from django.db import models

# Create your models here.
class Channel(models.Model):
    id = models.CharField(max_length=24, primary_key=True) # ID of the channel as generated by YouTube - i.e. youtube.com/channel/<id>
    name = models.TextField(null=False, blank=False)

    class Meta:
        managed = True
        db_table = "channel"

class Category(models.Model):
    # The category that YouTube has the video tagged as
    id = models.AutoField(primary_key=True)
    name = models.TextField(unique=True, null=False, blank=False)

    class Meta:
        managed = True
        verbose_name_plural = "Categories"
        db_table = "category"
    
class Video(models.Model):
    id = models.CharField(max_length=11, primary_key=True) # ID of the video as generated by YouTube - i.e. youtube.com/watch?v=<id>
    url = models.URLField()
    title = models.TextField(null=False, blank=False)
    transcript = models.TextField() # File path
    summary = models.TextField(null=False, blank=True) # Summary generated by OpenAI
    channel = models.ForeignKey(Channel, on_delete=models.RESTRICT, null=False)
    publication_date = models.DateTimeField()
    category = models.ForeignKey(Category, on_delete=models.RESTRICT, null=False)

    class Meta:
        managed = True
        db_table = "video"
