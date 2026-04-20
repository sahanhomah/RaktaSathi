from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from .models import BloodRequest


@receiver(pre_save, sender=BloodRequest)
def delete_replaced_prescription_image(sender, instance, **kwargs):
	if not instance.pk:
		return

	try:
		existing = sender.objects.get(pk=instance.pk)
	except sender.DoesNotExist:
		return

	existing_file = existing.prescription_image
	new_file = instance.prescription_image
	if existing_file and existing_file.name and existing_file.name != getattr(new_file, 'name', ''):
		existing_file.delete(save=False)


@receiver(post_delete, sender=BloodRequest)
def delete_prescription_image_on_delete(sender, instance, **kwargs):
	if instance.prescription_image:
		instance.prescription_image.delete(save=False)