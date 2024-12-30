import os
import argparse
from dotenv import load_dotenv
from youtube_handler import YoutubeHandler
from transcript_processor import TranscriptProcessor
from markdown_generator import MarkdownGenerator
from utils import (
    TimingStats, 
    create_progress, 
    measure_time, 
    save_markdown, 
    print_configuration,
    SystemInfo,
    console,
    load_transcripts,
    save_transcripts,
    TranscriptData
)
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    # Load environment variables first
    # Add debug information for .env loading
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        console.log(f"[cyan]Loading environment from: {env_path}[/cyan]")
    else:
        console.log("[yellow]Warning: .env file not found[/yellow]")
    
    # Get playlist URL from environment
    env_playlist_url = os.getenv('PLAYLIST_URL') or None  # Convert empty string to None
    if env_playlist_url:
        console.log(f"[green]Found playlist URL in environment:[/green] {env_playlist_url}")
    else:
        console.log("[yellow]No playlist URL found in environment[/yellow]")
    
    # Get system information
    system_settings = SystemInfo.get_optimal_settings(
        verbose=os.getenv('VERBOSE', '').lower() in ('true', '1', 'yes')
    )
    
    # Get environment variables with defaults
    env_videos = os.getenv('VIDEOS', '')  # Empty string as default
    env_categories = os.getenv('CATEGORIES')
    env_batch_size = os.getenv('BATCH_SIZE', '1')
    env_num_gpus = os.getenv('NUM_GPUS', str(system_settings['num_gpus']))
    env_num_cpus = os.getenv('NUM_CPUS', str(system_settings['num_cpus']))
    env_model = os.getenv('MODEL', 'llama3.2')
    env_threads = os.getenv('THREADS', str(system_settings['num_threads']))
    env_output = os.getenv('OUTPUT')
    env_verbose = os.getenv('VERBOSE', '').lower() in ('true', '1', 'yes')
    
    parser = argparse.ArgumentParser(description='Analyze YouTube playlist')
    parser.add_argument('--playlist-url', type=str, 
        help='YouTube playlist URL (overrides environment variable)',
        default=env_playlist_url)
    parser.add_argument('--videos', type=int, 
        help='Number of videos to process (default: all)', 
        default=int(env_videos) if env_videos.isdigit() else None)
    parser.add_argument('--categories', type=str,
        help='Comma-separated list of categories to include',
        default=env_categories)
    parser.add_argument('--batch-size', type=int,
        help='Number of videos to process concurrently (default: 1)',
        default=int(env_batch_size))
    parser.add_argument('--num-gpus', type=int,
        help='Number of GPUs to use (default: 0)',
        default=int(env_num_gpus))
    parser.add_argument('--num-cpus', type=int,
        help='Number of CPU cores to use (default: 4)',
        default=int(env_num_cpus))
    parser.add_argument('-o', '--output', type=str,
        help='Output file path (default: auto-generated in output/)',
        default=env_output)
    parser.add_argument('--model', type=str,
        help='Ollama model to use (default: llama3.2)',
        default=env_model)
    parser.add_argument('--threads', type=int,
        help='Number of CPU threads for LLM (default: 4)',
        default=int(env_threads))
    parser.add_argument('--verbose', action='store_true',
        help='Show detailed progress information',
        default=env_verbose)
    parser.add_argument('--extract-transcripts', type=str,
        help='Extract transcripts and save to specified zip file')
    parser.add_argument('--with-transcripts', type=str,
        help='Use previously extracted transcripts from zip file')
    args = parser.parse_args()
    
    # If playlist_url is not provided in command line, use environment variable
    if not args.playlist_url:
        args.playlist_url = env_playlist_url
    
    return args

def get_playlist_url(args) -> str:
    """Get playlist URL from arguments or environment."""
    if not args.playlist_url:
        console.log("[yellow]No playlist URL provided in environment or command line[/yellow]")
        return input("Please enter the YouTube playlist URL: ")
    
    return args.playlist_url

def process_video(video, youtube_handler, transcript_processor, progress=None, verbose=False, timing_stats=None) -> dict:
    """Process a single video and return result."""
    # Create formatted title
    video_title = f"[green]{video['title']}[/green]"
    
    # Get task IDs from progress context
    tasks = progress.task_ids if progress else []
    overall_task = tasks[0] if tasks else None
    
    if progress and verbose:
        progress.log(f"[bold white]Processing:[/bold white] {video_title}")
    
    if progress:
        progress.update(overall_task, advance=0.25, description=f"[yellow]Downloading transcript for: {video['title']}")
    
    # Get transcript with status
    transcript = measure_time("Transcript Download", youtube_handler.get_transcript, timing_stats, video['video_id'])
    
    if not transcript:
        if progress and verbose:
            progress.log(f"[yellow]Skipping:[/yellow] {video_title} [dim](No transcript available)[/dim]")
        if progress:
            progress.update(overall_task, advance=0.75)  # Complete remaining progress for skipped video
        return None
    
    try:
        # First get and check category
        if progress and verbose:
            progress.log(f"[bold white]Categorizing:[/bold white] {video_title}")
        if progress:
            progress.update(overall_task, advance=0.25, description=f"[yellow]Categorizing: {video['title']}")
        
        category = measure_time("Category Generation", transcript_processor.get_category, timing_stats, video['title'], transcript)
        
        # Check if category matches filter
        if not transcript_processor.matches_filter(category):
            if progress and verbose:
                progress.log(f"[yellow]Skipping:[/yellow] {video_title} [dim](Category '{category}' not in filter)[/dim]")
            if progress:
                progress.update(overall_task, advance=0.5)  # Complete remaining progress for filtered video
            return None
        
        # If category matches, get summary
        if progress and verbose:
            progress.log(f"[bold white]Generating summary for:[/bold white] {video_title}")
        if progress:
            progress.update(overall_task, advance=0.25, description=f"[yellow]Generating summary for: {video['title']}")
        
        summary = measure_time("Summary Generation", transcript_processor.get_summary, timing_stats, video['title'], transcript)
        
        # Return combined results
        result = {
            "category": category,
            "summary": summary
        }
        
        if progress and verbose:
            progress.log(f"[green]Completed:[/green] {video_title}")
        if progress:
            progress.update(overall_task, advance=0.25, description="[yellow]Processing videos...")
        
        return result
        
    except Exception as e:
        if progress and verbose:
            progress.log(f"[red]Error processing[/red] {video_title}: [dim]{str(e)}[/dim]")
        if progress:
            progress.update(overall_task, advance=1.0)  # Complete progress for errored video
        return None

def process_video_batch(videos, youtube_handler, transcript_processor, markdown_generator, batch_size=1, progress=None, overall_task=None, timing_stats=None):
    """Process a batch of videos concurrently."""
    with ThreadPoolExecutor(max_workers=batch_size) as executor:
        # Submit all tasks
        future_to_video = {
            executor.submit(
                process_video,
                video,
                youtube_handler,
                transcript_processor,
                progress,
                True if timing_stats else False,  # verbose mode
                timing_stats
            ): video for video in videos
        }
        
        # Process completed tasks as they finish
        for future in as_completed(future_to_video):
            # Process result if valid
            result = future.result()
            if result:
                markdown_generator.add_video(
                    result['category'],
                    future_to_video[future],
                    result['summary']
                )

def process_playlist(videos, youtube_handler, transcript_processor, markdown_generator, verbose=False, timing_stats=None):
    """Process all videos in the playlist."""
    batch_size = transcript_processor.batch_size
    total_videos = len(videos)
    
    with create_progress() as progress:
        # Create tasks for each phase
        overall_task = progress.add_task(
            description=f"[yellow]Processing {total_videos} videos",
            total=total_videos
        )
        
        for i in range(0, len(videos), batch_size):
            batch = videos[i:i + batch_size]
            
            if verbose:
                task = progress.tasks[overall_task]
                if task.speed:
                    # Convert speed from videos/second to videos/minute
                    speed_per_minute = task.speed * 60
                    progress.log(f"Processing rate: {speed_per_minute:.1f} videos/minute")
                
            process_video_batch(
                batch,
                youtube_handler,
                transcript_processor,
                markdown_generator,
                batch_size,
                progress,
                overall_task,
                timing_stats
            )

def main():
    # Initialize
    args = parse_arguments()
    timing_stats = TimingStats() if args.verbose else None
    
    # Get playlist information first
    playlist_url = get_playlist_url(args)
    
    # Print configuration if verbose mode is enabled
    print_configuration(args, playlist_url)
    
    # Load saved transcripts if provided
    saved_transcripts = None
    if args.with_transcripts:
        saved_transcripts = load_transcripts(args.with_transcripts)
        print(f"\nLoaded {len(saved_transcripts)} transcripts from {args.with_transcripts}")
    
    # Setup components
    youtube_handler = YoutubeHandler(verbose=args.verbose, saved_transcripts=saved_transcripts)
    
    # Get playlist information
    videos, playlist_title = youtube_handler.get_playlist_videos(playlist_url)
    
    # If we're just extracting transcripts, do that and exit
    if args.extract_transcripts:
        transcripts = {}
        for video in videos:
            transcript = youtube_handler.get_transcript(video['video_id'])
            transcripts[video['video_id']] = TranscriptData(
                video_id=video['video_id'],
                title=video['title'],
                url=video['url'],
                description=video['description'],
                transcript=transcript,
                timestamp=datetime.now()
            )
        save_transcripts(transcripts, args.extract_transcripts)
        print(f"\nSaved {len(transcripts)} transcripts to {args.extract_transcripts}")
        return
    
    # Set category filter if provided
    try:
        transcript_processor = TranscriptProcessor(
            batch_size=args.batch_size,
            num_gpus=args.num_gpus,
            num_cpus=args.num_cpus,
            model=args.model,
            num_threads=args.threads
        )
        transcript_processor.set_filter_categories(args.categories)
        if args.categories:
            print(f"\nFiltering videos by categories: {args.categories}")
    except ValueError as e:
        print(f"\nError: {str(e)}")
        return
    
    # Initialize markdown generator with playlist title
    markdown_generator = MarkdownGenerator(playlist_title)
    
    # Limit videos if specified
    if args.videos is not None:
        videos = videos[:args.videos]
        print(f"\nProcessing first {args.videos} video(s) from playlist")
    else:
        print(f"\nProcessing all {len(videos)} videos from playlist")
    
    # Process videos
    process_playlist(videos, youtube_handler, transcript_processor, markdown_generator, args.verbose, timing_stats)
    
    # Check if any videos were processed
    if not markdown_generator.categories:
        print("\nNo videos matched the specified categories.")
        return
    
    # Generate and save output
    markdown_content = markdown_generator.generate_markdown()
    output_filename = save_markdown(
        markdown_content, 
        playlist_title, 
        args.videos,
        "_filtered" if args.categories else None,
        args.output
    )
    
    print(f"\nSummary saved to: {output_filename}")
    
    # Print timing statistics if in verbose mode
    if timing_stats:
        timing_stats.print_stats()

if __name__ == "__main__":
    main() 