"""
Image optimization service for better performance
"""

import os
import asyncio
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from PIL import Image, ImageOps
import aiofiles
from io import BytesIO
import structlog

logger = structlog.get_logger()

class ImageOptimizer:
    """Image optimization service"""
    
    def __init__(self):
        self.supported_formats = {'JPEG', 'PNG', 'WEBP', 'AVIF'}
        self.quality_settings = {
            'thumbnail': 85,
            'small': 90,
            'medium': 85,
            'large': 80,
            'original': 95
        }
        
        # Size presets
        self.size_presets = {
            'thumbnail': (300, 300),
            'small': (600, 400),
            'medium': (1200, 800),
            'large': (1920, 1280),
            'hero': (2560, 1440)
        }
    
    async def optimize_image(
        self,
        input_path: Path,
        output_dir: Path,
        filename_base: str,
        generate_webp: bool = True,
        generate_sizes: bool = True
    ) -> Dict[str, Any]:
        """
        Optimize image and generate multiple sizes and formats
        """
        try:
            # Ensure output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Open and process image
            with Image.open(input_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Create white background for transparency
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Auto-orient image based on EXIF data
                img = ImageOps.exif_transpose(img)
                
                original_size = img.size
                results = {
                    'original_size': original_size,
                    'optimized_images': {},
                    'total_size_reduction': 0,
                    'formats_generated': []
                }
                
                # Generate different sizes
                if generate_sizes:
                    for size_name, target_size in self.size_presets.items():
                        # Skip if original is smaller than target
                        if original_size[0] <= target_size[0] and original_size[1] <= target_size[1]:
                            if size_name == 'thumbnail':
                                # Always generate thumbnail
                                resized_img = img.copy()
                            else:
                                continue
                        else:
                            # Resize maintaining aspect ratio
                            resized_img = img.copy()
                            resized_img.thumbnail(target_size, Image.Resampling.LANCZOS)
                        
                        # Save JPEG version
                        jpeg_path = output_dir / f"{filename_base}_{size_name}.jpg"
                        await self._save_image_async(
                            resized_img, jpeg_path, 'JPEG',
                            quality=self.quality_settings.get(size_name, 85)
                        )
                        
                        results['optimized_images'][f'{size_name}_jpeg'] = {
                            'path': str(jpeg_path),
                            'size': resized_img.size,
                            'format': 'JPEG',
                            'file_size': jpeg_path.stat().st_size if jpeg_path.exists() else 0
                        }
                        
                        # Save WebP version if requested
                        if generate_webp:
                            webp_path = output_dir / f"{filename_base}_{size_name}.webp"
                            await self._save_image_async(
                                resized_img, webp_path, 'WEBP',
                                quality=self.quality_settings.get(size_name, 85)
                            )
                            
                            results['optimized_images'][f'{size_name}_webp'] = {
                                'path': str(webp_path),
                                'size': resized_img.size,
                                'format': 'WEBP',
                                'file_size': webp_path.stat().st_size if webp_path.exists() else 0
                            }
                
                # Calculate total size reduction
                original_file_size = input_path.stat().st_size
                total_optimized_size = sum(
                    img_info['file_size'] for img_info in results['optimized_images'].values()
                )
                
                results['original_file_size'] = original_file_size
                results['total_optimized_size'] = total_optimized_size
                results['size_reduction_percent'] = (
                    (original_file_size - total_optimized_size) / original_file_size * 100
                    if original_file_size > 0 else 0
                )
                
                logger.info(
                    f"Image optimization completed",
                    original_size=original_size,
                    variants_generated=len(results['optimized_images']),
                    size_reduction=f"{results['size_reduction_percent']:.1f}%"
                )
                
                return results
                
        except Exception as e:
            logger.error(f"Image optimization failed: {e}")
            raise
    
    async def _save_image_async(
        self,
        image: Image.Image,
        output_path: Path,
        format: str,
        quality: int = 85
    ):
        """Save image asynchronously"""
        def save_image():
            save_kwargs = {'format': format, 'optimize': True}
            
            if format == 'JPEG':
                save_kwargs.update({
                    'quality': quality,
                    'progressive': True
                })
            elif format == 'WEBP':
                save_kwargs.update({
                    'quality': quality,
                    'method': 6  # Best compression
                })
            elif format == 'PNG':
                save_kwargs.update({
                    'optimize': True,
                    'compress_level': 9
                })
            
            image.save(output_path, **save_kwargs)
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, save_image)
    
    async def generate_responsive_images(
        self,
        input_path: Path,
        output_dir: Path,
        base_name: str
    ) -> Dict[str, str]:
        """Generate responsive images for web use"""
        
        responsive_images = {}
        
        try:
            with Image.open(input_path) as img:
                # Auto-orient
                img = ImageOps.exif_transpose(img)
                
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Generate different sizes for responsive design
                sizes = {
                    'xs': 480,   # Mobile
                    'sm': 768,   # Tablet
                    'md': 1024,  # Desktop
                    'lg': 1440,  # Large desktop
                    'xl': 1920   # Extra large
                }
                
                for size_name, width in sizes.items():
                    if img.width <= width:
                        # Don't upscale
                        continue
                    
                    # Calculate height maintaining aspect ratio
                    height = int((width / img.width) * img.height)
                    
                    # Resize image
                    resized = img.resize((width, height), Image.Resampling.LANCZOS)
                    
                    # Save WebP (modern format)
                    webp_path = output_dir / f"{base_name}_{size_name}.webp"
                    await self._save_image_async(resized, webp_path, 'WEBP', quality=85)
                    responsive_images[f'{size_name}_webp'] = str(webp_path)
                    
                    # Save JPEG (fallback)
                    jpeg_path = output_dir / f"{base_name}_{size_name}.jpg"
                    await self._save_image_async(resized, jpeg_path, 'JPEG', quality=85)
                    responsive_images[f'{size_name}_jpeg'] = str(jpeg_path)
                
                return responsive_images
                
        except Exception as e:
            logger.error(f"Responsive image generation failed: {e}")
            return {}
    
    def get_image_info(self, image_path: Path) -> Dict[str, Any]:
        """Get image information"""
        try:
            with Image.open(image_path) as img:
                return {
                    'size': img.size,
                    'format': img.format,
                    'mode': img.mode,
                    'has_transparency': img.mode in ('RGBA', 'LA', 'P'),
                    'file_size': image_path.stat().st_size
                }
        except Exception as e:
            logger.error(f"Failed to get image info: {e}")
            return {}

# Global image optimizer instance
image_optimizer = ImageOptimizer()