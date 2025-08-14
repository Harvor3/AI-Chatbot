# Google AI Setup Guide

## 🤖 Using Google's Free Gemini Models

Your multi-agent RAG chatbot now supports Google's powerful Gemini models, which offer:
- **Free tier available** - No credit card required to start
- **High performance** - Gemini 1.5 Flash is fast and capable
- **Large context window** - Handle longer documents
- **Multimodal capabilities** - Text and image understanding

## 🔑 Getting Your Google AI API Key

### Option 1: Google AI Studio (Recommended for Development)

1. **Visit Google AI Studio**: https://aistudio.google.com/
2. **Sign in** with your Google account
3. **Click "Get API Key"** in the left sidebar
4. **Create new project** or select existing project
5. **Generate API key** - copy the key that starts with `AIza...`

### Option 2: Google Cloud Vertex AI (Enterprise)

1. **Visit Google Cloud Console**: https://console.cloud.google.com/
2. **Create or select a project**
3. **Enable the Vertex AI API**
4. **Set up authentication** (service account or application default credentials)
5. **Note your project ID and preferred location**

## ⚙️ Configuration

### Method 1: Environment File (Recommended)

Create or update your `.env` file:

```bash
# Google AI Studio API Key
GOOGLE_API_KEY=AIza_your_actual_api_key_here

# Optional: For Vertex AI instead
# GOOGLE_PROJECT_ID=your-google-cloud-project-id
# GOOGLE_LOCATION=us-central1
```

### Method 2: Environment Variables

Set environment variables directly:

```bash
# Windows
set GOOGLE_API_KEY=AIza_your_actual_api_key_here

# Linux/Mac
export GOOGLE_API_KEY=AIza_your_actual_api_key_here
```

## 🚀 Available Models

The system will automatically use these Google models in priority order:

1. **Gemini 1.5 Flash** (via Google AI Studio API)
   - Fast and efficient
   - Great for most use cases
   - Free tier: 15 requests per minute

2. **Gemini 1.5 Flash** (via Vertex AI)
   - Enterprise features
   - Higher rate limits
   - Pay-per-use pricing

## ✅ Verification

After setting up your API key:

1. **Restart the application**:
   ```bash
   streamlit run app.py
   ```

2. **Check the sidebar** - you should see:
   - ✅ Google AI API Key configured
   - 🤖 Using Gemini 1.5 Flash model

3. **Test with a query** like:
   - "Hello, introduce yourself"
   - "What can you help me with?"

## 🚀 Gemini Model Features

| Feature | Gemini 1.5 Flash | Details |
|---------|------------------|---------|
| **Free Tier** | ✅ Yes | No credit card required |
| **Speed** | ⚡ Very Fast | Optimized for quick responses |
| **Context Window** | 📚 1M tokens | Handle very long documents |
| **Multimodal** | ✅ Yes | Text and image understanding |
| **Rate Limits** | 15/min free | Generous free tier limits |

## 🔧 Troubleshooting

### "No valid API key found"
- Check your `.env` file exists in the project root
- Verify the API key format starts with `AIza`
- Restart the Streamlit application

### "API key invalid"
- Regenerate your API key in Google AI Studio
- Check for extra spaces or characters
- Ensure the API key is active

### "Quota exceeded"
- You've hit the free tier limits (15 requests/minute)
- Wait a minute and try again
- Consider upgrading to paid tier for higher limits

## 💡 Pro Tips

1. **Free Tier Limits**: Gemini 1.5 Flash free tier allows 15 requests per minute
2. **Context Window**: Gemini can handle very long documents (up to 1M tokens)
3. **No Fallback Needed**: System is designed to work exclusively with Google AI
4. **Cost Effective**: Google AI Studio is completely free for development and testing
5. **Enterprise Ready**: Upgrade to Vertex AI for production workloads

## 🔗 Useful Links

- [Google AI Studio](https://aistudio.google.com/)
- [Gemini API Documentation](https://ai.google.dev/docs)
- [Google Cloud Vertex AI](https://cloud.google.com/vertex-ai)
- [Pricing Information](https://ai.google.dev/pricing)

---

**Your RAG chatbot is now powered by Google's cutting-edge Gemini models!** 🚀 