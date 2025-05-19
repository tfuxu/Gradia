import subprocess
import os
from .gradient import GradientBackground
from .background import Background
import queue
import time
import threading
import re


class ImageBackground(Background):
    def __init__(self, background_image_path, resize="fill"):
        self.background_image_path = background_image_path
        self.resize = resize  # options: none, fill, fit, stretch

    def prepare_command(self, width, height):
        resize_command = []

        if self.resize == "fill":
            resize_command = ["-resize", f"{width}x{height}^", "-gravity", "center", "-extent", f"{width}x{height}"]
        elif self.resize == "fit":
            resize_command = ["-resize", f"{width}x{height}"]
        elif self.resize == "stretch":
            resize_command = ["-resize", f"{width}x{height}!"]

        return [
            self.background_image_path,
            *resize_command
        ]

    def get_name(self):
        filename = os.path.basename(self.background_image_path)
        return f"image-{filename}-{self.resize}"

class Text:
    def __init__(self, text, font="Adwaita-Sans-Bold", color="white", size=42, gravity="south"):
        self.text = text
        self.font = font
        self.color = color
        self.size = size
        self.gravity = gravity

    def prepare_command(self, width, height, padding=10):
        offset_x = 0
        offset_y = 0

        g = self.gravity.lower()

        if "west" in g:
            offset_x = padding
        elif "east" in g:
            offset_x = padding

        if "north" in g:
            offset_y = padding
        elif "south" in g:
            offset_y = padding

        return [
            "-font", self.font,
            "-pointsize", str(self.size),
            "-fill", self.color,
            "-gravity", self.gravity,
            "-annotate", f"+{offset_x}+{offset_y}", self.text
        ]

    def get_available_fonts(self):
        try:
            command = ["magick", "convert", "-list", "font"]
            result = subprocess.run(command, capture_output=True, text=True, check=True)

            return result
        except (subprocess.CalledProcessError, FileNotFoundError):
            return

class ProcessingTask:
    def __init__(self, image_path, output_path, callback=None):
        self.image_path = image_path
        self.output_path = output_path
        self.callback = callback
        self.timestamp = time.time()

class ProcessingQueue:
    def __init__(self, max_queue_size=10):
        self.queue = queue.Queue(maxsize=max_queue_size)
        self.current_task = None
        self.processing = False
        self.lock = threading.Lock()
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()

    def add_task(self, processor, image_path, output_path, callback=None):
        task = ProcessingTask(image_path, output_path, callback)

        with self.lock:
            new_queue = queue.Queue(maxsize=self.queue.maxsize)
            skipped = 0

            try:
                while True:
                    old_task = self.queue.get_nowait()
                    if old_task.output_path != output_path:
                        new_queue.put(old_task)
                    else:
                        skipped += 1
            except queue.Empty:
                pass
            self.queue = new_queue
            if skipped > 0:
                print(f"Skipped {skipped} older tasks for {output_path}")
            try:
                self.queue.put_nowait((processor, task))
                print(f"Added task for {output_path} to the queue")
                return True
            except queue.Full:
                print(f"Queue is full, couldn't add task for {output_path}")
                return False

    def _process_queue(self):
        while True:
            try:
                processor, task = self.queue.get()

                with self.lock:
                    self.current_task = task
                    self.processing = True

                print(f"Processing task for {task.output_path}")
                try:
                    processor.process(task.image_path, task.output_path)
                    success = True
                    print(f"Successfully processed {task.output_path}")
                except Exception as e:
                    success = False
                    print(f"Error processing {task.output_path}: {e}")
                self.queue.task_done()

                with self.lock:
                    self.current_task = None
                    self.processing = False

                if task.callback:
                    try:
                        task.callback(success)
                    except Exception as e:
                        print(f"Error in callback: {e}")

            except Exception as e:
                print(f"Error in queue processing: {e}")
                time.sleep(0.1)

            time.sleep(0.01)

    def is_processing(self, output_path=None):
        with self.lock:
            if not self.processing:
                return False
            if output_path is None:
                return True
            return self.current_task and self.current_task.output_path == output_path

    def clear_queue(self):
        with self.lock:
            try:
                while True:
                    self.queue.get_nowait()
                    self.queue.task_done()
            except queue.Empty:
                pass
            return True

class ImageProcessor:
    def __init__(
        self,
        background=None,
        padding=20,
        aspect_ratio=None,
        text=None
    ):
        self.background = background
        self.padding = padding
        self.aspect_ratio = aspect_ratio
        self.text = text

    def process_async(self, image_path, output_path, callback=None):
        return processing_queue.add_task(self, image_path, output_path, callback)

    def process(self, image_path, output_path):
        # Check if input file exists
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Input image not found: {image_path}")

        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        process_id = int(time.time() * 1000)
        temp_dir = f"{output_path}.tmp.{process_id}"
        os.makedirs(temp_dir, exist_ok=True)

        try:
            width, height = self._get_image_dimensions(image_path)

            # Handle negative padding (cropping)
            temp_image = None
            if self.padding < 0:
                temp_image = os.path.join(temp_dir, "cropped.png")
                image_path, width, height = self._crop_image(image_path, temp_image, width, height)

            padded_width, padded_height = self._calculate_dimensions(width, height)
            temp_output = os.path.join(temp_dir, "processed.png")
            success = self._apply_background(image_path, temp_output, padded_width, padded_height)

            if success and os.path.exists(temp_output) and self.text:
                self._apply_text(temp_output, padded_width, padded_height)
            if success and os.path.exists(temp_output):
                if os.path.exists(output_path):
                    os.remove(output_path)
                os.rename(temp_output, output_path)
                return True
            else:
                print(f"Failed to process image (no output file was created)")
                return False

        except Exception as e:
            print(f"Error during image processing: {e}")
            return False
        finally:
            # Clean up temporary directory
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                print(f"Warning: Failed to remove temporary directory {temp_dir}: {e}")

    def _get_image_dimensions(self, image_path):
        commands = [
            ["magick", "identify", "-format", "%w %h", image_path],
            ["identify", "-format", "%w %h", image_path]
        ]

        for cmd in commands:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                width, height = map(int, result.stdout.strip().split())
                return width, height
            except Exception as e:
                print(f"Warning: Command {cmd} failed: {e}")
                continue

        try:
            from PIL import Image
            with Image.open(image_path) as img:
                return img.width, img.height
        except Exception as e:
            print(f"Warning: PIL fallback failed: {e}")

        # If all methods fail, return default dimensions
        print("Warning: Using default dimensions 1000x1000")
        return 1000, 1000

    def _crop_image(self, image_path, temp_path, width, height):
        crop_width = max(1, width + 2 * self.padding)
        crop_height = max(1, height + 2 * self.padding)

        offset_x = (width - crop_width) // 2
        offset_y = (height - crop_height) // 2

        try:
            # Try with magick command
            crop_cmd = [
                "magick",
                image_path,
                "-crop", f"{crop_width}x{crop_height}+{offset_x}+{offset_y}",
                temp_path
            ]
            subprocess.run(crop_cmd, check=True, capture_output=True)

            # Verify the file was created
            if os.path.exists(temp_path):
                return temp_path, crop_width, crop_height
            else:
                print(f"Warning: Crop operation didn't produce output file: {temp_path}")
        except Exception as e:
            print(f"Warning: Crop operation failed: {e}")

        return image_path, width, height

    def _calculate_dimensions(self, width, height):
        if self.padding >= 0:
            padded_width = width + self.padding * 2
            padded_height = height + self.padding * 2
        else:
            padded_width, padded_height = width, height

        if self.aspect_ratio:
            padded_width, padded_height = self._adjust_for_aspect_ratio(padded_width, padded_height)

        return padded_width, padded_height

    def _adjust_for_aspect_ratio(self, width, height):
        try:
            # Parse aspect ratio as float or from string like "16:9"
            if isinstance(self.aspect_ratio, str) and ":" in self.aspect_ratio:
                w, h = map(float, self.aspect_ratio.split(":"))
                target_ratio = w / h
            else:
                target_ratio = float(self.aspect_ratio)

            current_ratio = width / height

            if current_ratio < target_ratio:
                adjusted_width = int(height * target_ratio)
                return adjusted_width, height
            elif current_ratio > target_ratio:
                adjusted_height = int(width / target_ratio)
                return width, adjusted_height

            return width, height
        except Exception as e:
            print(f"Warning: Error adjusting aspect ratio: {e}")
            return width, height

    def _apply_background(self, image_path, output_path, width, height):
        try:
            cmd = ["magick"]

            # Get background command from background object
            background_cmd = self.background.prepare_command(width, height)
            cmd.extend(background_cmd)

            # Add source image with padding if needed
            if self.padding >= 0:
                cmd.extend([
                    "(",
                    image_path,
                    "-bordercolor", "none",
                    "-border", str(self.padding),
                    ")"
                ])
            else:
                cmd.append(image_path)

            # Complete the composition
            cmd.extend([
                "-gravity", "center",
                "-compose", "over",
                "-composite",
                output_path
            ])

            # Run the command and check for errors
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)

            # Verify the output file was created
            if os.path.exists(output_path):
                return True
            else:
                print(f"Warning: Background application didn't produce output file: {output_path}")
                # Try to show the actual command that was run
                print(f"Command was: {' '.join(cmd)}")
                return False

        except Exception as e:
            print(f"Error: ImageMagick processing failed during background application: {e}")
            # Try to show the actual command that was run
            if 'cmd' in locals():
                print(f"Command was: {' '.join(cmd)}")
            return False

    def _apply_text(self, image_path, width, height):
        if not self.text or not str(self.text).strip():
            return

        if not os.path.exists(image_path):
            print(f"Error: Cannot apply text, image doesn't exist: {image_path}")
            return

        try:
            # Create a copy of the image as backup in case text application fails
            backup_path = f"{image_path}.bak"
            if os.path.exists(image_path):
                import shutil
                shutil.copy2(image_path, backup_path)
            else:
                print(f"Error: Cannot create backup, source image doesn't exist: {image_path}")
                return


            cmd = ["magick", image_path]
            text_cmd = self.text.prepare_command(width, height)
            cmd.extend(text_cmd)
            cmd.append(image_path)

            result = subprocess.run(cmd, check=True, capture_output=True, text=True)

            if os.path.exists(backup_path):
                os.remove(backup_path)

        except Exception as e:
            print(f"Error: ImageMagick processing failed during text application: {e}")
            if 'cmd' in locals():
                print(f"Command was: {' '.join(cmd)}")

            # Restore the backup if it exists
            if os.path.exists(backup_path):
                print("Restoring image from backup after text application failed")
                try:
                    if os.path.exists(image_path):
                        os.remove(image_path)
                    import shutil
                    shutil.copy2(backup_path, image_path)
                    os.remove(backup_path)
                except Exception as restore_error:
                    print(f"Error restoring backup: {restore_error}")
