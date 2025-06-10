# 🐳 SolarScope Pro - Docker Deployment

Complete containerized deployment for the SolarScope Pro solar monitoring platform.

## 🚀 Quick Start

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ RAM
- 10GB+ disk space

### Development Environment

```bash
# Clone and setup
git clone <repository>
cd solar-monitor

# Start development environment
./scripts/deploy.sh dev

# View logs
./scripts/deploy.sh logs --follow

# Stop services
./scripts/deploy.sh stop
```

Access the application:
- **API**: http://localhost:8000
- **Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health

### Production Environment

```bash
# Setup production environment
cp config/.env.production config/.env
# Edit config/.env with your settings

# Start production environment with Nginx
./scripts/deploy.sh prod

# Check status
./scripts/deploy.sh status
```

## 📋 Services

| Service | Port | Description |
|---------|------|-------------|
| `solarscope-api` | 8000 | FastAPI application |
| `timescaledb` | 5432 | TimescaleDB database |
| `redis` | 6379 | Redis cache (optional) |
| `nginx` | 80/443 | Reverse proxy (production) |

## 🔧 Configuration

### Environment Variables

Copy `config/.env.production` to `config/.env` and customize:

```bash
# Database
TIMESCALE_HOST=timescaledb
TIMESCALE_PASSWORD=your-secure-password
TIMESCALE_DATABASE=solarscope_pro

# Security
SECRET_KEY=your-super-secret-key-here

# Monitoring
SCAN_INTERVAL=1.0
LOG_LEVEL=INFO
```

### Hardware Access

For Raspberry Pi I2C sensor access:
```bash
# Add to docker-compose.yml volumes:
- /dev/i2c-1:/dev/i2c-1
```

## 📊 Monitoring & Logs

```bash
# View service status
./scripts/deploy.sh status

# View logs
./scripts/deploy.sh logs

# Follow logs in real-time
./scripts/deploy.sh logs --follow

# View specific service logs
docker-compose logs solarscope-api
```

## 🔄 Management Commands

```bash
# Build/rebuild images
./scripts/deploy.sh build
./scripts/deploy.sh build --rebuild

# Restart services
./scripts/deploy.sh restart

# Clean up (removes volumes!)
./scripts/deploy.sh clean
```

## 🗄️ Database Management

### Backup Database
```bash
docker-compose exec timescaledb pg_dump -U solarscope solarscope_pro > backup.sql
```

### Restore Database
```bash
docker-compose exec -T timescaledb psql -U solarscope solarscope_pro < backup.sql
```

### Connect to Database
```bash
docker-compose exec timescaledb psql -U solarscope -d solarscope_pro
```

## 🌐 Production Deployment

### SSL/TLS Setup

1. Obtain SSL certificates
2. Place in `ssl/` directory
3. Update `config/nginx.conf`
4. Start with production profile:

```bash
./scripts/deploy.sh prod
```

### Resource Requirements

**Minimum:**
- 2 CPU cores
- 4GB RAM
- 20GB storage

**Recommended:**
- 4 CPU cores
- 8GB RAM
- 50GB SSD storage

### Performance Tuning

Edit `docker-compose.yml`:

```yaml
solarscope-api:
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 2G
      reservations:
        cpus: '1.0'
        memory: 1G
```

## 🔍 Troubleshooting

### Common Issues

**Database connection failed:**
```bash
# Check TimescaleDB status
docker-compose logs timescaledb

# Restart database
docker-compose restart timescaledb
```

**API not responding:**
```bash
# Check API logs
docker-compose logs solarscope-api

# Rebuild and restart
./scripts/deploy.sh build --rebuild
./scripts/deploy.sh restart
```

**Permission denied on I2C:**
```bash
# Add user to i2c group (on host)
sudo usermod -a -G i2c $USER

# Restart Docker daemon
sudo systemctl restart docker
```

### Health Checks

```bash
# API health
curl http://localhost:8000/api/v1/health

# Database health
docker-compose exec timescaledb pg_isready -U solarscope

# Redis health
docker-compose exec redis redis-cli ping
```

## 📁 Volume Mounts

| Volume | Purpose | Backup Required |
|--------|---------|-----------------|
| `timescale_data` | Database storage | ✅ Critical |
| `redis_data` | Cache storage | ❌ Optional |
| `./logs` | Application logs | ❌ Optional |

## 🔒 Security

### Production Checklist

- [ ] Change default passwords
- [ ] Generate secure SECRET_KEY
- [ ] Setup SSL certificates
- [ ] Configure firewall rules
- [ ] Enable log rotation
- [ ] Setup monitoring alerts
- [ ] Regular security updates

### Network Security

Default network: `172.20.0.0/16`

Services are isolated within Docker network. Only exposed ports are accessible from host.

## 📈 Scaling

### Horizontal Scaling

```yaml
solarscope-api:
  deploy:
    replicas: 3
  # Add load balancer
```

### Database Scaling

TimescaleDB supports:
- Read replicas
- Distributed hypertables
- Connection pooling with PgBouncer

## 🆘 Support

For issues and questions:
1. Check logs: `./scripts/deploy.sh logs`
2. Review health status: `./scripts/deploy.sh status`
3. Consult troubleshooting section above
