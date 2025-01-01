import re
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    MofNCompleteColumn,
    TimeElapsedColumn,
    ProgressColumn
)
from rich.console import Console
from rich.text import Text
from collections import defaultdict
from time import time
from datetime import datetime, timedelta
import os
import psutil
import platform
import multiprocessing
import subprocess
from shutil import which
import pickle
from dataclasses import dataclass
from typing import Dict, Optional

console = Console()

class ETAColumn(ProgressColumn):
    """Renders estimated completion time."""
    def __init__(self):
        super().__init__()
        self.start_time = time()

    @property
    def _header(self) -> Text:
        """Get the header text for the column."""
        return Text("ETA", style="cyan", justify="right")

    def render(self, task):
        """Render the ETA column."""
        if task.finished:
            return Text("Done!")
        
        elapsed = time() - self.start_time
        if task.speed is None or elapsed < 1:
            return Text("calculating...")
        
        remaining = task.total - task.completed
        eta_seconds = remaining / task.speed
        eta_time = datetime.now() + timedelta(seconds=eta_seconds)
        return Text(f"ETA: {eta_time.strftime('%H:%M:%S')}", style="cyan", justify="right")

def sanitize_filename(title: str) -> str:
    """Convert title to a valid filename."""
    sanitized = re.sub(r'[^\w\s-]', '', title.lower())
    sanitized = re.sub(r'[-\s]+', '_', sanitized)
    return sanitized.strip('_')

def create_progress() -> Progress:
    """Create a custom progress bar."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description:<30}"),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        ETAColumn(),
        expand=True,
        transient=False,
        console=console
    )

def measure_time(operation: str, func, timing_stats=None, *args, **kwargs):
    """Measure time taken by an operation."""
    start_time = time()
    result = func(*args, **kwargs)
    if timing_stats:
        timing_stats.add_timing(operation, time() - start_time)
    return result

def save_markdown(content: str, playlist_title: str, num_videos: int = None, suffix: str = None, output_path: str = None) -> str:
    """Save markdown content to file and return filename."""
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return output_path
    
    os.makedirs('output', exist_ok=True)
    filename_prefix = sanitize_filename(playlist_title)
    if num_videos is not None:
        filename_prefix += f"_first_{num_videos}"
    if suffix:
        filename_prefix += suffix
    output_filename = f"output/{filename_prefix}.md"
    
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return output_filename

def print_configuration(args, playlist_url):
    """Print current configuration in a colorful format."""
    if not args.verbose:
        return
    
    console.print("\n[bold cyan]Configuration:[/bold cyan]")
    console.print("┌" + "─" * 50 + "┐")
    
    # Playlist settings
    console.print("│ [yellow]Playlist Settings[/yellow]")
    console.print(f"│ • URL: [green]{playlist_url}[/green]")
    
    # Processing settings
    console.print("│ [yellow]Processing Settings[/yellow]")
    console.print(f"│ • Videos to process: [green]{args.videos if args.videos else 'all'}[/green]")
    console.print(f"│ • Batch size: [green]{args.batch_size}[/green]")
    
    # Hardware settings
    console.print("│ [yellow]Hardware Settings[/yellow]")
    console.print(f"│ • GPUs: [green]{args.num_gpus}[/green]")
    console.print(f"│ • CPU cores: [green]{args.num_cpus}[/green]")
    console.print(f"│ • Threads: [green]{args.threads}[/green]")
    
    # Model settings
    console.print("│ [yellow]Model Settings[/yellow]")
    console.print(f"│ • Model: [green]{args.model}[/green]")
    
    # Filter settings
    console.print("│ [yellow]Filter Settings[/yellow]")
    console.print(f"│ • Categories: [green]{args.categories if args.categories else 'all'}[/green]")
    
    # Output settings
    console.print("│ [yellow]Output Settings[/yellow]")
    console.print(f"│ • Output path: [green]{args.output if args.output else 'auto'}[/green]")
    console.print(f"│ • Verbose mode: [green]{'enabled' if args.verbose else 'disabled'}[/green]")
    
    console.print("└" + "─" * 50 + "┘\n")

class TimingStats:
    def __init__(self):
        self.timings = defaultdict(list)
    
    def add_timing(self, operation: str, duration: float):
        """Add a timing measurement for an operation."""
        self.timings[operation].append(duration)
    
    def print_stats(self):
        """Print formatted timing statistics."""
        if not self.timings:
            return
        
        console.print("\n[bold cyan]Timing Statistics:[/bold cyan]")
        console.print("┌" + "─" * 50 + "┐")
        
        for operation in sorted(self.timings.keys()):
            times = self.timings[operation]
            avg_time = sum(times) / len(times)
            console.print(f"│ [yellow]{operation}[/yellow]")
            console.print(f"│ • Average time: [green]{avg_time:.2f}s[/green]")
            console.print(f"│ • Total calls: [green]{len(times)}[/green]")
        
        console.print("└" + "─" * 50 + "┘\n") 

class SystemInfo:
    """Detect and provide system hardware information."""
    
    @staticmethod
    def get_gpu_count(verbose: bool = False) -> int:
        """Get number of available GPUs."""
        system = platform.system()
        
        if system == "Darwin":  # macOS
            try:
                # Check if ioreg exists
                if not which('ioreg'):
                    if verbose:
                        console.log("[yellow]Warning: ioreg not found, defaulting to 1 GPU[/yellow]")
                    return 1
                
                # Use ioreg to detect GPUs and their cores
                result = subprocess.run(['ioreg', '-l', '-w', '0'], 
                                     capture_output=True, text=True)
                
                # Look for GPUConfigurationVariable
                for line in result.stdout.split('\n'):
                    if 'GPUConfigurationVariable' in line:
                        # Extract the JSON-like string
                        config_start = line.find('{')
                        if config_start != -1:
                            config_str = line[config_start:]
                            # Parse num_cores from the configuration
                            if '"num_cores"=' in config_str:
                                num_cores = int(config_str.split('"num_cores"=')[1].split(',')[0])
                                return num_cores
                
                # Fallback to checking for GPU devices if configuration not found
                gpu_count = len([line for line in result.stdout.split('\n') 
                                if any(gpu_identifier in line 
                                      for gpu_identifier in ['GPU', 'Metal'])])
                
                if gpu_count == 0:
                    # Check if system_profiler exists
                    if not which('system_profiler'):
                        if verbose:
                            console.log("[yellow]Warning: system_profiler not found, defaulting to 1 GPU[/yellow]")
                        return 1
                    
                    # Alternative method using system_profiler
                    result = subprocess.run(['system_profiler', 'SPDisplaysDataType'],
                                          capture_output=True, text=True)
                    gpu_count = len([line for line in result.stdout.split('\n')
                                    if any(gpu_identifier in line
                                          for gpu_identifier in ['Chipset Model:', 'Processor:'])])
                
                return max(1, gpu_count)  # At least 1 GPU if any graphics capability is detected
            except Exception as e:
                if verbose:
                    console.log(f"[yellow]Warning: Error detecting GPUs: {str(e)}[/yellow]")
                return 1  # Default to 1 on macOS as it always has some graphics capability
        elif system == "Linux":
            try:
                # Check for NVIDIA GPUs using nvidia-smi
                if which('nvidia-smi'):
                    result = subprocess.run(['nvidia-smi', '-L'], 
                                         capture_output=True, text=True)
                    return len(result.stdout.strip().split('\n'))
            except:
                pass
        elif system == "Windows":
            try:
                # Check for NVIDIA GPUs using nvidia-smi on Windows
                if which('nvidia-smi'):
                    result = subprocess.run(['nvidia-smi', '-L'], 
                                         capture_output=True, text=True, shell=True)
                    return len(result.stdout.strip().split('\n'))
            except:
                pass
        
        return 0  # Default to no GPUs if detection fails
    
    @staticmethod
    def get_cpu_count() -> int:
        """Get optimal number of CPU cores to use."""
        cpu_count = multiprocessing.cpu_count()
        # Reserve some cores for system operations
        recommended_cores = max(1, cpu_count - 2)
        return recommended_cores
    
    @staticmethod
    def get_memory_info() -> dict:
        """Get system memory information."""
        memory = psutil.virtual_memory()
        return {
            'total': memory.total,
            'available': memory.available,
            'percent': memory.percent,
            'recommended_threads': max(1, int(memory.available / (1024 * 1024 * 1024)))  # 1GB per thread
        }
    
    @classmethod
    def get_optimal_settings(cls, verbose: bool = False) -> dict:
        """Get recommended settings based on system capabilities."""
        memory_info = cls.get_memory_info()
        system = platform.system()
        
        settings = {
            'num_gpus': cls.get_gpu_count(verbose),
            'num_cpus': cls.get_cpu_count(),
            'num_threads': min(
                cls.get_cpu_count(),
                memory_info['recommended_threads']
            )
        }
        
        if verbose:
            # Log system information
            console.log(f"[bold cyan]System Information:[/bold cyan]")
            console.log(f"• System: {system}")
            console.log(f"• CPU cores available: {multiprocessing.cpu_count()}")
            console.log(f"• GPUs available: {settings['num_gpus']}")
            console.log(f"• Memory available: {memory_info['available'] / (1024**3):.1f}GB")
            console.log(f"• Memory usage: {memory_info['percent']}%")
            console.log("\n[bold cyan]Recommended Settings:[/bold cyan]")
            console.log(f"• Number of GPUs: {settings['num_gpus']}")
            console.log(f"• Number of CPUs: {settings['num_cpus']}")
            console.log(f"• Number of threads: {settings['num_threads']}")
        
        return settings 