# Tailscale Setup — Connect Local Ollama

## Mục đích

Pio_lab chạy trên 1 máy (vd: laptop dev), Ollama chạy trên máy khác (vd: PC GPU).
Tailscale tạo VPN mesh, cho phép Pio_lab gọi Ollama qua IP private 100.x.x.x.

## Setup

### 1. Cài Tailscale trên CẢ HAI máy

- https://tailscale.com/download

### 2. Login bằng cùng tài khoản

```bash
sudo tailscale up
```

Lấy IP Tailscale của máy chạy Ollama: `tailscale ip -4`
Vd: `100.64.10.5`

### 3. Cấu hình Ollama listen tất cả interfaces

```bash
# Trên máy Ollama (Linux/Mac)
OLLAMA_HOST=0.0.0.0:11434 ollama serve

# Hoặc set permanent
export OLLAMA_HOST=0.0.0.0:11434
```

### 4. Cập nhật .env trên máy Pio_lab

```ini
OLLAMA_HOST=http://100.64.10.5:11434
OLLAMA_DEFAULT_MODEL=gpt-oss-20b
```

### 5. Test

```bash
curl http://100.64.10.5:11434/api/tags
```

## Bảo mật

- Tailscale traffic mã hóa end-to-end (WireGuard)
- ACL: limit chỉ máy Pio_lab được gọi Ollama port
- KHÔNG expose Ollama ra public Internet
