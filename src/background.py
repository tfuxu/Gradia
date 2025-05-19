from abc import ABC, abstractmethod
class Background(ABC):
    @abstractmethod
    def prepare_command(self, width, height):
        """Return the ImageMagick command parts for creating this background."""
        pass

    @abstractmethod
    def get_name(self):
        """Return a descriptive name for this background type."""
        pass

