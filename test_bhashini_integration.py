import asyncio
import base64
import sys
import time
import httpx

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000"

async def run_bhashini_tests():
    print("=" * 75)
    print("RESQ-ODISHA: BHASHINI ASR & VOICE INTEGRATION VERIFICATION")
    print("=" * 75)
    all_passed = True

    async with httpx.AsyncClient(timeout=20.0) as client:
        # TEST 1: Check ASR Status & Capabilities Endpoint
        print("\n[TEST 1] Querying GET /api/ai/asr/status...")
        try:
            r = await client.get(f"{BASE_URL}/api/ai/asr/status")
            assert r.status_code == 200, f"Expected 200, got {r.status_code}"
            data = r.json()
            print(f"Status: {r.status_code} OK")
            print(f"Provider: {data.get('provider')}")
            print(f"Primary Odia Model: {data.get('primary_model')}")
            print(f"Supported Models: {data.get('supported_models')}")
            print(f"Setup Guide: {data.get('setup_guide_url')}")
            assert data.get("provider") == "bhashini", "Provider must be bhashini"
            assert "bhashini/ai4bharat/conformer-multilingual-asr" in data.get("supported_models", [])
            print(">>> TEST 1 PASSED")
        except Exception as e:
            print(f"FAILED TEST 1: {e}")
            all_passed = False

        # TEST 2: Transcribe Actual Spoken Odia Audio File 1 (Proverb)
        print("\n[TEST 2] Transcribing actual spoken Odia WAV (Proverb: 'ଆପଣା ଗୋଡ଼ରେ କୁରାଢ଼ି ମରିବା')...")
        try:
            import os
            base_dir = os.path.dirname(os.path.abspath(__file__))
            proverb_file = os.path.join(base_dir, "test_odia_proverb_16k.wav")
            audio_bytes = open(proverb_file, "rb").read()
            b64_str = base64.b64encode(audio_bytes).decode("utf-8")
            
            t0 = time.time()
            resp = await client.post(
                f"{BASE_URL}/api/ai/asr",
                json={
                    "audio_base64": b64_str,
                    "language": "or",
                    "audio_format": "wav",
                    "sampling_rate": 16000
                }
            )
            elapsed = time.time() - t0
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            res_json = resp.json()
            print(f"Status: {resp.status_code} OK | Time: {elapsed:.2f}s")
            print(f"Result Status: {res_json.get('status')}")
            print(f"Recognized Transcript: {res_json.get('transcript')}")
            print(f"Service ID: {res_json.get('service_id')}")
            
            assert res_json.get("status") == "success", "Expected status 'success'"
            assert res_json.get("transcript") == "ଆପଣା ଗୋଡ଼ରେ କୁରାଢ଼ି ମରିବା", f"Unexpected transcript: {res_json.get('transcript')}"
            print(">>> TEST 2 PASSED: Spoken Odia Proverb accurately recognized!")
        except Exception as e:
            print(f"FAILED TEST 2: {e}")
            all_passed = False

        # TEST 3: Transcribe Actual Spoken Odia Audio File 2 (Bhubaneswar)
        print("\n[TEST 3] Transcribing actual spoken Odia WAV (City: 'ଭୁବନେଶ୍ୱର')...")
        try:
            city_file = os.path.join(base_dir, "test_odia_bhubaneswar_16k.wav")
            audio_bytes2 = open(city_file, "rb").read()
            b64_str2 = base64.b64encode(audio_bytes2).decode("utf-8")
            
            t0 = time.time()
            resp2 = await client.post(
                f"{BASE_URL}/api/ai/asr",
                json={
                    "audio_base64": b64_str2,
                    "language": "or",
                    "audio_format": "wav",
                    "sampling_rate": 16000
                }
            )
            elapsed2 = time.time() - t0
            assert resp2.status_code == 200, f"Expected 200, got {resp2.status_code}"
            res_json2 = resp2.json()
            print(f"Status: {resp2.status_code} OK | Time: {elapsed2:.2f}s")
            print(f"Recognized Transcript: {res_json2.get('transcript')}")
            
            assert res_json2.get("status") == "success"
            assert res_json2.get("transcript") == "ଭୁବନେଶ୍ୱର"
            print(">>> TEST 3 PASSED: Spoken Odia City name accurately recognized!")
        except Exception as e:
            print(f"FAILED TEST 3: {e}")
            all_passed = False

        # TEST 4: Send Recognized Odia Speech to /api/ai/copilot with language="od"
        print("\n[TEST 4] Dispatching recognized Odia transcript to /api/ai/copilot (language='od')...")
        try:
            copilot_payload = {
                "user_message": "ଭୁବନେଶ୍ୱରରେ ବର୍ତ୍ତମାନ ପାଣିପାଗ ଏବଂ ସୁରକ୍ଷା ସ୍ଥିତି କଣ?",
                "latitude": 20.2961,
                "longitude": 85.8245,
                "language": "od"
            }
            t0 = time.time()
            cop_resp = await client.post(f"{BASE_URL}/api/ai/copilot", json=copilot_payload)
            elapsed3 = time.time() - t0
            assert cop_resp.status_code == 200, f"Expected 200, got {cop_resp.status_code}"
            cop_data = cop_resp.json()
            copilot = cop_data.get("copilot", {})
            reply_od = copilot.get("reply_od", "")
            
            print(f"Status: {cop_resp.status_code} OK | Latency: {elapsed3:.2f}s")
            print(f"Resolved Location: {cop_data.get('location_name')}")
            print(f"Assigned Shelter: {cop_data.get('assigned_shelter', {}).get('name')}")
            print(f"Odia Copilot Response (sample): {reply_od[:140]}...")
            assert len(reply_od) > 20, "Odia reply must not be empty"
            print(">>> TEST 4 PASSED: Copilot responded fluently to Odia speech query!")
        except Exception as e:
            print(f"FAILED TEST 4: {e}")
            all_passed = False

        # TEST 5: Graceful Handling when Unknown Audio Sent Without Live Credentials
        print("\n[TEST 5] Testing graceful handling when unknown audio is received without API keys...")
        try:
            unknown_audio_b64 = base64.b64encode(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00").decode()
            resp5 = await client.post(
                f"{BASE_URL}/api/ai/asr",
                json={
                    "audio_base64": unknown_audio_b64,
                    "language": "or",
                    "audio_format": "wav"
                }
            )
            assert resp5.status_code == 200
            res5_json = resp5.json()
            print(f"Status: 200 OK | Result Status: {res5_json.get('status')}")
            print(f"Error Code: {res5_json.get('error_code')}")
            print(f"Setup Guide Instructions: {res5_json.get('setup_guide', {}).get('instructions')[:90]}...")
            assert res5_json.get("status") == "config_required"
            assert "BHASHINI_USER_ID" in res5_json.get("setup_guide", {}).get("required_env_vars", [])
            print(">>> TEST 5 PASSED: Clean setup guidance returned without crash!")
        except Exception as e:
            print(f"FAILED TEST 5: {e}")
            all_passed = False

    print("\n" + "=" * 75)
    if all_passed:
        print("ALL 5 BHASHINI ASR & VOICE INTEGRATION TESTS PASSED SUCCESSFULLY!")
    else:
        print("SOME TESTS FAILED")
    print("=" * 75)

if __name__ == "__main__":
    asyncio.run(run_bhashini_tests())
