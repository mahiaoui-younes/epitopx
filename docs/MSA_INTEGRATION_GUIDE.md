# MSA API Integration & Deployment Guide

## 🔗 Integration Patterns

### 1. Frontend Integration (JavaScript/React)

```javascript
// utils/msaService.js
const MSA_BASE_URL = 'http://localhost:8000/api/msa';

export const performAlignment = async (sequences, options = {}) => {
  const payload = {
    sequences,
    match: options.match || 1,
    mismatch: options.mismatch || -1,
    gap: options.gap || -2,
  };

  const response = await fetch(`${MSA_BASE_URL}/align/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`MSA API error: ${response.statusText}`);
  }

  return response.json();
};

export const getStatistics = async (sequences) => {
  const response = await fetch(`${MSA_BASE_URL}/statistics/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sequences }),
  });

  return response.json();
};

// React Component Example
import React, { useState } from 'react';

function AlignmentViewer() {
  const [alignment, setAlignment] = useState([]);
  const [consensus, setConsensus] = useState('');
  const [loading, setLoading] = useState(false);

  const handleAlign = async (sequences) => {
    setLoading(true);
    try {
      const result = await performAlignment(sequences);
      if (result.success) {
        setAlignment(result.alignment);
        setConsensus(result.consensus);
      } else {
        alert(`Error: ${result.error}`);
      }
    } catch (error) {
      alert(`Failed to align: ${error.message}`);
    }
    setLoading(false);
  };

  return (
    <div>
      <button onClick={() => handleAlign(['ATCG', 'ATCG', 'TTTT'])}>
        Align Sequences
      </button>
      {loading && <p>Aligning...</p>}
      {alignment.length > 0 && (
        <div>
          <h3>Alignment Result</h3>
          {alignment.map((seq, i) => (
            <div key={i}><code>{seq}</code></div>
          ))}
          <h4>Consensus: <code>{consensus}</code></h4>
        </div>
      )}
    </div>
  );
}

export default AlignmentViewer;
```

### 2. Python Integration

```python
# Django view using MSA service
from django.http import JsonResponse
from rest_framework.decorators import api_view
from bioinformatics.services import MSAService

@api_view(['POST'])
def my_analysis_view(request):
    """Custom analysis using MSA"""
    sequences = request.data.get('sequences', [])
    
    service = MSAService()
    result = service.align(sequences)
    
    if result['success']:
        # Do additional analysis
        alignment = result['alignment']
        consensus = result['consensus']
        
        # Your custom logic here
        return JsonResponse({
            'status': 'success',
            'alignment': alignment,
            'consensus': consensus,
            'custom_analysis': perform_custom_analysis(alignment)
        })
    else:
        return JsonResponse({'error': result['error']}, status=400)

# Direct service usage
from bioinformatics.services import MSAService

service = MSAService(match=2, mismatch=-2, gap=-3)
result = service.align(['ATCG', 'ATCG', 'TTTT'])

print(f"Consensus: {result['consensus']}")
print(f"Alignment length: {result['alignment_length']}")
```

### 3. Microservice Integration

```python
# Celery task for async MSA
from celery import shared_task
from bioinformatics.services import MSAService

@shared_task
def align_sequences_async(sequences, job_id):
    """Async alignment task"""
    service = MSAService()
    result = service.align(sequences)
    
    # Store result in cache or database
    cache.set(f'msa_result_{job_id}', result, timeout=3600)
    
    return result

# Usage in view
from celery.result import AsyncResult

def start_alignment(request):
    sequences = request.data.get('sequences')
    job = align_sequences_async.delay(sequences, job_id='xyz123')
    
    return JsonResponse({'task_id': job.id})

def get_alignment_result(request, task_id):
    result = AsyncResult(task_id)
    
    if result.ready():
        return JsonResponse({'result': result.result})
    else:
        return JsonResponse({'status': 'pending'})
```

### 4. Command-Line Tool

```bash
#!/bin/bash
# msa_cli.sh - Command-line wrapper for MSA API

if [ $# -lt 2 ]; then
    echo "Usage: $0 <sequences_json> [options]"
    echo "Example: $0 '{\"sequences\": [\"ATCG\", \"ATCG\"]}'"
    exit 1
fi

SEQUENCES=$1
OPTIONS=${2:-'{}'}

curl -X POST http://localhost:8000/api/msa/align/ \
  -H "Content-Type: application/json" \
  -d "{\"sequences\": $SEQUENCES}" | python -m json.tool
```

---

## 🐳 Docker Deployment

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy code
COPY backend_api/ .

# Run migrations and server
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  django:
    build: .
    ports:
      - "8000:8000"
    environment:
      DEBUG: "False"
      ALLOWED_HOSTS: "localhost,127.0.0.1"
    volumes:
      - ./backend_api:/app
```

---

## ☁️ Cloud Deployment (Azure)

### Azure Container Instances
```bash
# Build and push to ACR
az acr build --registry myregistry --image msa-api:latest .

# Deploy to Container Instances
az container create \
  --resource-group mygroup \
  --name msa-api \
  --image myregistry.azurecr.io/msa-api:latest \
  --ports 8000 \
  --cpu 2 --memory 1
```

### Azure App Service
```bash
# Deploy Django app
az webapp create \
  --resource-group mygroup \
  --plan myplan \
  --name msa-api-app \
  --runtime "PYTHON:3.11"

# Configure and deploy
az webapp config appsettings set \
  --resource-group mygroup \
  --name msa-api-app \
  --settings DEBUG=False ALLOWED_HOSTS="*.azurewebsites.net"

# Deploy code
az webapp deployment source config-zip \
  --resource-group mygroup \
  --name msa-api-app \
  --src deploy.zip
```

---

## 🔒 Security Considerations

### Input Validation
✅ Implemented: Size limits (50 sequences, 10,000 bp each)
✅ Implemented: Character validation (DNA only)
✅ Implemented: Type checking

### Recommendations
```python
# settings.py - Add these for production
ALLOWED_HOSTS = ['your-domain.com']
DEBUG = False
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
CORS_ALLOWED_ORIGINS = [
    'https://your-frontend.com',
]

# Rate limiting
from rest_framework.throttling import UserRateThrottle

class MSAThrottle(UserRateThrottle):
    scope = 'msa'
    THROTTLE_RATES = {
        'msa': '100/hour',
    }

# Apply to views
class MSAViewSet(viewsets.ViewSet):
    throttle_classes = [MSAThrottle]
```

---

## 📊 Monitoring & Logging

### Logging Configuration
```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'msa_api.log',
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 5,
        },
    },
    'loggers': {
        'bioinformatics': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

### Application Insights (Azure)
```python
# Enable Application Insights
from opencensus.ext.django.middleware import OpencensusMiddleware

MIDDLEWARE = [
    'opencensus.ext.django.middleware.OpencensusMiddleware',
    ...
]

OPENCENSUS = {
    'TRACE': {
        'SAMPLER': 'opencensus.trace.samplers.AlwaysOnSampler()',
        'EXPORTER': 'opencensus_ext_azure.trace_exporter.AzureExporter()',
    }
}
```

---

## 🧪 Testing in Production

### Integration Tests
```python
import requests
import time

def test_msa_api_production():
    """Test production API endpoint"""
    url = 'https://msa-api.example.com/api/msa/health/'
    
    response = requests.get(url, timeout=5)
    assert response.status_code == 200
    assert response.json()['status'] == 'healthy'

def test_alignment_performance():
    """Test alignment performance under load"""
    sequences = ['ATCG' * 250 for _ in range(10)]  # 10 × 1000 bp
    
    start = time.time()
    response = requests.post(
        'https://msa-api.example.com/api/msa/align/',
        json={'sequences': sequences},
        timeout=30
    )
    elapsed = time.time() - start
    
    assert response.status_code == 200
    assert elapsed < 10, f"Took {elapsed}s, expected < 10s"
```

---

## 📈 Scaling Considerations

### Performance Optimization
1. **Caching**: Cache distance matrices for repeated sequences
2. **Async Processing**: Use Celery for long-running alignments
3. **Load Balancing**: Deploy multiple instances behind load balancer
4. **Database**: Use PostgreSQL for result storage

### Example with Redis Caching
```python
from django.core.cache import cache
from bioinformatics.services import MSAService

def align_with_cache(sequences_tuple):
    """Align with result caching"""
    cache_key = f"msa_{''.join(sequences_tuple)}"
    
    # Check cache first
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    # Perform alignment
    service = MSAService()
    result = service.align(list(sequences_tuple))
    
    # Cache for 1 hour
    cache.set(cache_key, result, timeout=3600)
    
    return result
```

---

## 🚀 Deployment Checklist

- [ ] Update `settings.py`:
  - [ ] Set `DEBUG = False`
  - [ ] Configure `ALLOWED_HOSTS`
  - [ ] Enable HTTPS/SSL
  - [ ] Set secure cookies

- [ ] Database:
  - [ ] Run migrations: `python manage.py migrate`
  - [ ] Create admin user: `python manage.py createsuperuser`
  - [ ] Backup database

- [ ] Static Files:
  - [ ] Run `python manage.py collectstatic`
  - [ ] Configure CDN/media server

- [ ] Dependencies:
  - [ ] Pin versions in `requirements.txt`
  - [ ] Test in production environment

- [ ] Monitoring:
  - [ ] Set up logging
  - [ ] Configure alerting
  - [ ] Monitor API response times

- [ ] Testing:
  - [ ] Run full test suite
  - [ ] Integration tests
  - [ ] Load tests
  - [ ] Security scan

- [ ] Documentation:
  - [ ] Update API docs
  - [ ] Create deployment runbook
  - [ ] Document scaling procedures

---

## 🔄 CI/CD Pipeline Example

### GitHub Actions
```yaml
name: Deploy MSA API

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - run: pip install -r requirements.txt
      - run: python manage.py test bioinformatics
      
  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: success()
    steps:
      - uses: actions/checkout@v2
      - uses: azure/container-instances-deploy-action@v1
        with:
          resource-group: ${{ secrets.RESOURCE_GROUP }}
          name: msa-api
          image: ${{ secrets.ACR_LOGIN_SERVER }}/msa-api:${{ github.sha }}
```

---

## 📞 Support & Troubleshooting

### Common Issues

**API not responding**
- Check if Django is running: `curl http://localhost:8000/api/msa/health/`
- Check Django logs for errors
- Verify port 8000 is accessible

**Slow alignments**
- Check sequence length (max 10,000 bp)
- Check number of sequences (max 50)
- Consider using async processing for large jobs
- Profile code to identify bottlenecks

**Memory issues**
- Reduce sequence length
- Process fewer sequences at once
- Use pagination for batch jobs
- Monitor memory usage

**Invalid sequence errors**
- Ensure only A, T, C, G characters
- No spaces or lowercase u (protein sequence)
- Remove any FASTA headers from sequences

---

## 📚 Additional Resources

- [Django Deployment](https://docs.djangoproject.com/en/stable/howto/deployment/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Docker Documentation](https://docs.docker.com/)
- [Azure App Service](https://docs.microsoft.com/azure/app-service/)

---

## Summary

The MSA API is now fully integrated and ready for:
- ✅ Frontend integration
- ✅ Microservice deployment
- ✅ Cloud hosting
- ✅ Container deployment
- ✅ Scaling to production load
