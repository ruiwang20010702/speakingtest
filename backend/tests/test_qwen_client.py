"""
Qwen-Omni Gateway Test
Tests the Part 2 evaluation functionality.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.adapters.gateways.qwen_client import QwenOmniGateway, Part2EvaluationResult


# Sample test questions
TEST_QUESTIONS = [
    {"no": 1, "question": "What is your name?", "reference_answer": "My name is..."},
    {"no": 2, "question": "How old are you?", "reference_answer": "I am ... years old."},
    {"no": 3, "question": "What color is this?", "reference_answer": "It is red/blue/green."},
    {"no": 4, "question": "What day is today?", "reference_answer": "Today is Monday/Tuesday..."},
    {"no": 5, "question": "How is the weather?", "reference_answer": "It is sunny/rainy..."},
    {"no": 6, "question": "What is your favorite food?", "reference_answer": "I like pizza/rice..."},
    {"no": 7, "question": "Do you have any pets?", "reference_answer": "Yes, I have a dog/cat..."},
    {"no": 8, "question": "What do you like to do?", "reference_answer": "I like to play/read..."},
    {"no": 9, "question": "Where do you live?", "reference_answer": "I live in..."},
    {"no": 10, "question": "What is your favorite color?", "reference_answer": "My favorite color is..."},
    {"no": 11, "question": "How many people are in your family?", "reference_answer": "There are ... people."},
    {"no": 12, "question": "What time do you go to bed?", "reference_answer": "I go to bed at..."},
]


async def test_qwen_gateway(audio_path: str):
    """Test Qwen-Omni gateway with a sample audio file."""
    
    print("=" * 60)
    print("Qwen-Omni Gateway Test")
    print("=" * 60)
    
    # Load audio file
    audio_file = Path(audio_path)
    if not audio_file.exists():
        print(f"Error: Audio file not found: {audio_path}")
        print("\nUsage: python test_qwen_client.py <audio_file.mp3>")
        return
    
    audio_data = audio_file.read_bytes()
    audio_format = audio_file.suffix[1:]  # Remove leading dot
    
    print(f"Audio file: {audio_path}")
    print(f"Audio size: {len(audio_data)} bytes")
    print(f"Audio format: {audio_format}")
    print()
    
    # Create gateway and evaluate
    gateway = QwenOmniGateway()
    
    print("Calling Qwen-Omni API...")
    print("(This may take 30-60 seconds)")
    print()
    
    result: Part2EvaluationResult = await gateway.evaluate_part2(
        audio_data=audio_data,
        audio_format=audio_format,
        questions=TEST_QUESTIONS
    )
    
    # Display results
    print("-" * 60)
    
    if result.success:
        print(f"✅ Evaluation Successful!")
        print()
        print(f"Total Score: {result.total_score}/24")
        print()
        print("Transcript:")
        print("-" * 40)
        print(result.transcript or "(No transcript)")
        print("-" * 40)
        print()
        print("Question-by-Question Scores:")
        for item in result.items or []:
            score = item.get("score_0_2", 0)
            emoji = "✅" if score == 2 else "⚠️" if score == 1 else "❌"
            print(f"  Q{item.get('no')}: {emoji} {score}/2 - {item.get('reason', '')[:50]}")
        
        print()
        print("Overall Suggestions:")
        for suggestion in result.overall_suggestion or []:
            print(f"  • {suggestion}")
    else:
        print(f"❌ Evaluation Failed: {result.error}")
        if result.raw_response:
            print()
            print("Raw Response:")
            print(result.raw_response[:500])
    
    print()
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_qwen_client.py <audio_file.mp3>")
        print("\nExample:")
        print("  python test_qwen_client.py ../../test_audio.mp3")
        sys.exit(1)
    
    audio_path = sys.argv[1]
    asyncio.run(test_qwen_gateway(audio_path))
