from django.db import models

# Create your models here.
class Channel(models.Model):
    id = models.CharField(max_length=24, primary_key=True)
    name = models.TextField(null=False, blank=False)

class Category(models.Model):
    # Will be: Top Stories, Sports, Entertainment, Science, Health, Business, Technology, National, or World
    id = models.AutoField(primary_key=True)
    name = models.TextField(unique=True, null=False, blank=False)
    
class Video(models.Model):
    id = models.CharField(max_length=11, primary_key=True)
    url = models.URLField()
    title = models.TextField(null=False, blank=False)
    transcript = models.TextField()
    channel = models.ForeignKey(Channel, on_delete=models.RESTRICT, null=False)
    publication_date = models.DateTimeField()
    category = models.ForeignKey(Category, on_delete=models.RESTRICT, null=False)
