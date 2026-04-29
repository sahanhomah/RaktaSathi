from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image, ImageFilter


ALLOWED_PRESCRIPTION_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
ALLOWED_PRESCRIPTION_CONTENT_TYPES = {'image/jpeg', 'image/png'}


def _max_upload_size_bytes() -> int:
	return int(getattr(settings, 'PRESCRIPTION_MAX_UPLOAD_BYTES', 5 * 1024 * 1024))


def _document_validation_thresholds() -> dict:
	return {
		'min_width': int(getattr(settings, 'PRESCRIPTION_DOC_MIN_WIDTH', 300)),
		'min_height': int(getattr(settings, 'PRESCRIPTION_DOC_MIN_HEIGHT', 300)),
		'min_bright_ratio': float(getattr(settings, 'PRESCRIPTION_DOC_MIN_BRIGHT_RATIO', 0.30)),
		'min_text_ratio': float(getattr(settings, 'PRESCRIPTION_DOC_MIN_TEXT_RATIO', 0.005)),
		'text_pixel_threshold': int(getattr(settings, 'PRESCRIPTION_DOC_TEXT_PIXEL_THRESHOLD', 140)),
		'min_edge_ratio': float(getattr(settings, 'PRESCRIPTION_DOC_MIN_EDGE_RATIO', 0.003)),
	}


def _validate_document_like_image(uploaded_file) -> None:
	thresholds = _document_validation_thresholds()

	try:
		uploaded_file.seek(0)
		with Image.open(uploaded_file) as image:
			image_format = (image.format or '').upper()
			if image_format not in {'JPEG', 'PNG'}:
				raise ValidationError('Only JPG and PNG files are allowed.')

			if image.width < thresholds['min_width'] or image.height < thresholds['min_height']:
				raise ValidationError(
					f'Prescription image must be at least {thresholds["min_width"]}x{thresholds["min_height"]} pixels.'
				)

			grayscale = image.convert('L')
			sample = grayscale.resize((200, 200))
			pixels = list(sample.getdata())
			total_pixels = len(pixels)

			bright_ratio = sum(1 for value in pixels if value >= 200) / total_pixels
			text_ratio = sum(1 for value in pixels if value <= thresholds['text_pixel_threshold']) / total_pixels

			edges = sample.filter(ImageFilter.FIND_EDGES)
			edge_pixels = list(edges.getdata())
			edge_ratio = sum(1 for value in edge_pixels if value >= 25) / total_pixels

			if bright_ratio < thresholds['min_bright_ratio']:
				raise ValidationError(
					'Prescription image must clearly show a document background.'
				)

			if text_ratio < thresholds['min_text_ratio']:
				raise ValidationError(
					'Prescription image must contain visible writing or text on the document.'
				)

			if edge_ratio < thresholds['min_edge_ratio']:
				raise ValidationError(
					'Prescription image appears unclear. Please upload a clearer document photo.'
				)
	except ValidationError:
		raise
	except Exception as exc:
		raise ValidationError('Upload a valid prescription image file.') from exc
	finally:
		uploaded_file.seek(0)


def validate_prescription_image(uploaded_file) -> None:
	if not uploaded_file:
		return

	file_extension = Path(uploaded_file.name).suffix.lower()
	if file_extension not in ALLOWED_PRESCRIPTION_EXTENSIONS:
		raise ValidationError('Only JPG and PNG files are allowed.')

	content_type = getattr(uploaded_file, 'content_type', '')
	if content_type and content_type.lower() not in ALLOWED_PRESCRIPTION_CONTENT_TYPES:
		raise ValidationError('Only JPG and PNG files are allowed.')

	max_size = _max_upload_size_bytes()
	if uploaded_file.size > max_size:
		max_size_mb = max_size / (1024 * 1024)
		raise ValidationError(f'Prescription image size must be {max_size_mb:g} MB or less.')

	_validate_document_like_image(uploaded_file)