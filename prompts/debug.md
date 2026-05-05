# Debug Template

## Khi test fail / code không work

```
@<file lỗi> @<test file> @terminal

Test này fail:
{paste test output / error trace}

Debug bằng cách:
1. **Reproduce locally** — chạy test, xác nhận fail
2. **Đọc trace** — locate file + line gây lỗi
3. **Hypothesis** — giải thích root cause (3 khả năng)
4. **Verify** — log debug, isolate variable
5. **Fix** — minimal change, KHÔNG refactor lan rộng
6. **Re-run** — confirm fix
7. **Add regression test** nếu bug tinh vi

KHÔNG được:
- Skip test (`@pytest.mark.skip`) thay vì fix
- Comment out code lỗi
- Catch exception rộng để giấu lỗi
- Modify test để pass mà chưa hiểu root cause

Output:
- Root cause (1-2 câu)
- Fix diff
- Test lại pass: ✓
```

## Khi LangGraph behavior lạ

```
@pio_lab/layer3_chief_of_staff/ @<state debug>

LangGraph graph behavior không đúng:
{describe bug, expected vs actual}

Debug LangGraph cụ thể:
1. **Check state mutation** — node có RETURN dict mới không (LangGraph requires immutable)?
2. **Check edges** — conditional edge function trả về đúng key?
3. **Check state schema** — TypedDict define đầy đủ field used?
4. **Check checkpointer** — state có persist giữa node calls?
5. **Add tracing** — `graph.compile(debug=True)` hoặc inject logger vào mỗi node

Pattern thường gặp:
- Mutation: `state["plan"].append(x)` ❌ → return `{"plan": state["plan"] + [x]}` ✓
- Missing key in conditional: trả "approval" mà edge map chỉ có "dispatch"
- Race condition: parallel nodes write same state field
```

## Khi provider không response

```
@pio_lab/providers/ @config/providers.yaml @.env

Provider call fail:
{paste error}

Debug provider:
1. **API key set?** — `echo $ANTHROPIC_API_KEY` (mask)
2. **Network reachable?** — curl test endpoint
3. **Tailscale up (Ollama)?** — `tailscale status`
4. **Routing chain correct?** — check `config/providers.yaml::routing_rules`
5. **Account quota?** — check provider dashboard
6. **Model name correct?** — provider có deprecate model?
7. **Rate limit?** — backoff + retry

Common fixes:
- ANTHROPIC_API_KEY chưa load .env → restart Cursor
- Ollama model chưa pull → `ollama pull <model>` trên máy Tailscale node
- Tool format sai → check @docs/PROVIDER_API_REFERENCE.md
```

## Khi DB error

```
@pio_lab/memory/postgres/ @docker-compose.yml

DB error:
{paste error}

Debug:
1. **Postgres up?** — `docker ps | grep postgres`
2. **Port free?** — `lsof -i :5432`
3. **Schema migrated?** — `alembic current`
4. **Connection string correct?** — check `.env::POSTGRES_*`
5. **Async session leak?** — check `async with` blocks

Fixes:
- Container stopped: `docker-compose restart postgres`
- Schema mismatch: `alembic upgrade head`
- Pool exhausted: increase `pool_size` in engine config
```
