name: Daily YouTube Shorts – 3 A.I. Prompts

on:
  schedule:
    - cron: '0 20 * * *'   # 20:00 UTC = 00:00 Dubai time
  workflow_dispatch:

jobs:
  create-and-upload:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      with:
        token: ${{ secrets.GITHUB_TOKEN }}
        fetch-depth: 0
        lfs: true

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install PyMuPDF moviepy google-api-python-client google-auth-oauthlib google-auth-httplib2 pillow numpy

    - name: Install FFmpeg
      run: |
        sudo apt-get update
        sudo apt-get install -y ffmpeg

    - name: Create client_secrets.json from secret
      run: |
        echo '${{ secrets.YOUTUBE_CLIENT_SECRETS }}' > client_secrets.json
        echo "✅ client_secrets.json created"

    - name: Decode token from secret
      run: |
        echo "${{ secrets.YOUTUBE_TOKEN_PICKLE }}" | base64 -d > token.pickle
        echo "✅ token.pickle restored"

    - name: Verify required files
      run: |
        if [ ! -f intros.json ]; then echo "❌ intros.json missing"; exit 1; fi
        if [ ! -f prompts.json ]; then echo "❌ prompts.json missing"; exit 1; fi
        if [ ! -d images ]; then echo "❌ images folder missing"; exit 1; fi
        echo "✅ All required files present"

    - name: Run Shorts video creation script
      run: python create_shorts_video.py

    - name: Upload video as artifact (debug)
      uses: actions/upload-artifact@v4
      with:
        name: shorts-video
        path: broke_to_fortune_500.mp4
        retention-days: 7