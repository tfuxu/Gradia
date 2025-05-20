from abc import ABC, abstractmethod


class Background(ABC):
    """
    Abstract base class for different backgrounds.
    
    All background implementations should inherit from this class
    and implement the required methods.
    """
    
    @abstractmethod
    def prepare_image(self, width, height):
        """
        Prepare and return a PIL Image with the background.
        
        Args:
            width (int): The target width
            height (int): The target height
            
        Returns:
            PIL.Image: The background image
        """
        pass
        
    @abstractmethod
    def get_name(self):
        """
        Get a unique identifier for this background.
        
        Returns:
            str: A unique name for this background configuration
        """
        pass