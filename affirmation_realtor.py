name: Upload Realtor Affirmation

on:
  schedule:
    # Runs daily at 9:00 AM Dubai time (5:00 UTC)
    - cron: '0 5 * * *'
  workflow_dispatch:

jobs:
  upload:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          persist-credentials: true
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install pillow moviepy google-api-python-client google-auth-oauthlib PyMuPDF numpy
          sudo apt-get update
          sudo apt-get install -y ffmpeg

      - name: Create directories
        run: |
          mkdir -p affirmation_pages
          mkdir -p daily_images

      - name: Decode Realtor token
        env:
          TOKEN: ${{ secrets.YOUTUBE_TOKEN_PICKLE_REALTOR }}
        run: |
          echo "$TOKEN" | base64 -d > token.pickle

      - name: Create client_secrets.json
        env:
          CLIENT_SECRETS: ${{ secrets.YOUTUBE_CLIENT_SECRETS }}
        run: |
          echo "$CLIENT_SECRETS" > client_secrets.json

      - name: Run Realtor Affirmation script
        run: python affirmation_realtor.py

      - name: Upload logs
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: realtor-affirmation-output
          path: |
            affirmation_pages/*.mp4
            affirmation_pages/*.png
