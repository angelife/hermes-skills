#!/usr/bin/env bash
# Batch-test hetaosu API keys against gy.hetaosu.xyz/v1/models
# Usage: bash scripts/batch-test-hetaosu-keys.sh
#
# Reads keys inline (hardcoded array below), tests each with a 10s timeout,
# prints ✅ for HTTP 200 or ❌ with HTTP status for failures.
# Outcome: a clean ✅ batch = all keys are valid at this moment.
set -euo pipefail

KEYS=(
  "test2-j02urx sk-8bWOZxxjbM25UfomzNezjyF47LljNRl16XD6qLwE8cRRKfsi"
  "test2-9n2lyz sk-WHYoZlCBnSMRCW7e5H9rB7eWDrS7iQkV8J1hfG6SDWiivVlO"
  "test2-5vxbv2 sk-ygb3sb1sLzXed0xcrEXyKQvmFgPmFLb35JIR0Pn2UbFhflCw"
  "test2-zcaftd sk-7Ax7P42cwbOXQKNAjD8ik0NRpZ7ulIwmVTRWD5c3Ch3yOkXg"
  "test2-0k45ck sk-1DI9DqegbMA3QgeetahNAYzDOwKMBuna36MELNm5NPOtYVnu"
  "test2-l1omdx sk-raIJj7RAH7rsk5J8xKxLTxpFZtUusXEbNPAmeLCm0BTbGJ4l"
  "test2-mm0tgz sk-fvrSs1ZD3L0GvhcQcwZWiI1UOeh7PS3vWgQWX1NnjtamPyDS"
  "test2-d57qw8 sk-cbb3CgGJg6T6UWj4eqiDI6hLG7JBTTqEeMxPFgJOooXj7B0D"
  "test2-u800e6 sk-hfYPaD0huso68aKocvcs6M1gZxZonN9zZjs2V7jEs92omHpt"
  "test2-p7p1me sk-F5jvF31brYmGJqFj6oj9ywE5fiv4ymfYLG5YtbSlqSlxXVBv"
  "test2-9585q7 sk-2TXXaUoL32pf6656nDZeLN5Am8A8KXtEddSs9z1H6LsD1Ero"
  "test2-9wygj3 sk-vD7Sugf2GpfyyLA3rLH7NqBCTt552XgI0bFphHjzuAaezAwr"
  "test2-n0x6zc sk-bZvM7621nlKBKBna8lCvKJbL03IAc9Jo3lAbyIAIEFZiihvZ"
  "test2-qghu5w sk-q1bAwXmg7OAOsPbY9esi6vw303MctVP9LTBiFfr9PwK5zsF0"
  "test2-oceis1 sk-XhfRYEHQ6qI2TpZeNdhZST3g0LCPo3Lps7hXiJAepBETyycN"
  "test2-4tvtlx sk-eAeMMIcaS5PzbqIwk2ISwx6MoO8mUhWjIbEEYnsk2Q0GzZs5"
  "test2-mlusgw sk-Zjbb79Sc4JgD4E1FiAsoTWEg2yzrbW9rTq7de0QeM7FeIxQi"
  "test2-vkslcw sk-7ci9UZjU4aE9xkwIG6iFsTbKxNKD6WQlu7NaQNdVDEJrbJfn"
  "test2-l9398l sk-q6OzsSzoi7jSW9sOL1w5RqHJ3riihY7B1AjNHmpaYroPbYa9"
  "test2 sk-U9UD7b6Xnm6zZXp4qKxOza5G5QC6knLSh6LdUde1IMRB8OpJ"
  "angelife-35ng2p sk-vPM03zhceMy5nlClAjFJvrzPLlj5iWVXNk4Hfnt7Q9xMlzC7"
  "angelife-aadnn0 sk-gZqC7TzikT8gI1dA9e6vqC0QutWsD4RzVZ84GOZCehzpaqvR"
  "angelife-mizxrt sk-vGLQh5winCGBdCuNHVqT3Hp5BrTosvskSx3boVOWoSyfurMG"
  "angelife-j9c2j1 sk-aY3BVvGSwvIWE3Iohdk3J37yHqJT3aCROBd2iK7YWbQvLHW9"
  "angelife-cx47k5 sk-RlAAAooRYwimwYw7mETl2OxUlQ6eBz9IQgLX0sUVzSPYeZU8"
  "angelife-x9y0dt sk-nu80cmzDzO5pHVOOmT9cULWUOA0VA82dNoChvuD8zrlMSAWJ"
  "angelife-3k8gun sk-VrQP08Uf2gPoI2SOa7XSKagJbmR1KE8WhyzG5zJ90NzfN8Gu"
  "angelife-4eim2m sk-674fegmKgEmJH6LSZQ09PeAAUeARaU6wGecGhIIFuEQMhxzZ"
  "angelife-401izf sk-v1mGIpRDOi2U383ZK0ONFuVprGZdxgw7OsrJrjZxdnDWbDG7"
  "angelife sk-MQ9DPpiFJRH9INK2WF2eoSegXPlPRcGYUEY60q2s1EIlBKvY"
  "test-th442x sk-5vSTIzrhe3ZIO7ofY7lt94ErJjsY27KkK1N7Iar7p7AlmF9D"
  "test-bgfww1 sk-QoDRYmZm7Oblb8oraI9Kuuji5fNIX1Ij2LxUhWc3O30hWHsS"
  "test-pp3vmz sk-ZDqPRfPpZ5l8gX8HneQdZUJdap8s9myTGMAuKljuF4oEgZkZ"
  "test-aeyw9y sk-rraFVzNPm3KZ2qcFdm5gY2GiU7RNlZmDmQei4mG2d22OBQjk"
  "test-35etvh sk-C0fVtpeER4jElJwKjkhoGiD9fjZShmy7TcM7dcnep4cN4jz6"
  "test-k1e4tx sk-CObB5tjczVLKGZWQTIvo58LYMuUPqLxZCUUVF9Rsnb0GkiwI"
  "test-k765y0 sk-4EpnI5Rgx8tV0VQg5F7W3cvkWeQB9fJrRudOtfT2dBCuAyHq"
  "test-egn740 sk-Mhy1q3fWT0Qiu7YYeOD48acwNF52URauapfrcEDLWMjNCdOe"
  "test-ef3tmb sk-tAm8NwtYXzpS3lwUmq1hQMjg20jgBPaWtcxws2tnSe6iKsWz"
  "test sk-YRodtz0ISk9yWVNmh5rRNxEugaRu5a5ofmbAYelmJM9pVnoe"
)

OK=0 FAIL=0
echo "=== hetaosu key test $(date) ==="
for entry in "${KEYS[@]}"; do
  name=$(echo "$entry" | awk '{print $1}')
  key=$(echo "$entry" | awk '{print $2}')
  http_code=$(curl -s -o /dev/null -w "%{http_code}" -m10 \
    https://gy.hetaosu.xyz/v1/models \
    -H "Authorization: Bearer $key" 2>/dev/null)
  if [ "$http_code" = "200" ]; then
    echo "✅ $name"
    OK=$((OK + 1))
  else
    echo "❌ $name (HTTP $http_code)"
    FAIL=$((FAIL + 1))
  fi
done
echo "=== $OK OK, $FAIL FAIL ==="
