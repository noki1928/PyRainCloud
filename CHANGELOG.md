# Changelog

Формат — [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/), версии — [SemVer](https://semver.org/lang/ru/).

## [0.1.0] — 2026-11-08

Первый выпуск (MVP).

### Добавлено

- `rc.raincloud(data, x, y, ...)` — rain cloud plot из pandas DataFrame: half-violin
  (KDE `scipy.stats.gaussian_kde`) + box plot + точки с jitter; возвращает `(Figure, Axes)`.
- Ориентация `orient='v' | 'h'`, палитра `palette`, параметры `cloud_alpha`, `cloud_width`,
  `point_size`, `point_alpha`, `box_width`, флаги `add_boxes` / `add_points`.
- Рисование на существующих осях (`ax=`) и воспроизводимый jitter (`random_state=`).
- Единый контракт ошибок (`ValueError` / `TypeError` с понятными сообщениями) и
  предупреждения `RaincloudWarning`: пропуски, нечисловые значения, малые и вырожденные
  выборки, больше 50 000 точек, больше 50 групп.
- Поддержка Python 3.9–3.13, pandas ≥ 1.5, matplotlib ≥ 3.5, numpy ≥ 1.22, scipy ≥ 1.8.
- Тесты критериев приёмки US1–US3, граничных случаев и производительности; CI на GitHub
  Actions (Linux / macOS / Windows и минимальные версии зависимостей).
- README, пример `examples/quickstart.ipynb`, инструкция пользователя в `docs/`.

[0.1.0]: https://github.com/noki1928/pyraincloud/releases/tag/v0.1.0
