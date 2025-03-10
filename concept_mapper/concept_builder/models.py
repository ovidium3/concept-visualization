from django.db import models


class Concept(models.Model):
    name = models.CharField(max_length=100)
    x_pos = models.FloatField(default=0.0)
    y_pos = models.FloatField(default=0.0)

    def __str__(self):
        return self.name


class Relation(models.Model):
    source = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name='outgoing')
    target = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name='incoming')

    def __str__(self):
        return f"{self.source} -> {self.target}"
