// Получаем CSRF-токен из cookie
function getCookie(name) {
    const v = document.cookie.split('; ').find(r => r.startsWith(name + '='));
    return v ? decodeURIComponent(v.split('=')[1]) : '';
}

const csrftoken = getCookie('csrftoken');

document.addEventListener('DOMContentLoaded', () => {
    const startBtn = document.getElementById('start-event-feedback');
    if (!startBtn) return;

    // При клике показываем форму
    startBtn.addEventListener('click', () => {
        document.getElementById('feedback-form-container').innerHTML = `
                    <div id="feedback-form" class="bg-white dark:bg-[#262626] rounded-2xl shadow p-6 space-y-4">
                      <label class="block text-sm font-medium mb-1">Рейтинг</label>
                      <div id="fb-stars" class="flex gap-1 text-3xl cursor-pointer select-none">
                        <span data-value="1" class="text-gray-400 hover:text-amber-300">☆</span>
                        <span data-value="2" class="text-gray-400 hover:text-amber-300">☆</span>
                        <span data-value="3" class="text-gray-400 hover:text-amber-300">☆</span>
                        <span data-value="4" class="text-gray-400 hover:text-amber-300">☆</span>
                        <span data-value="5" class="text-gray-400 hover:text-amber-300">☆</span>
                      </div>
                      <input type="hidden" id="fb-rating" name="rating" value="">
                      <label class="block text-sm font-medium">Комментарий</label>
                      <textarea id="fb-text" rows="4"
                                class="w-full rounded-lg border-gray-300 dark:border-gray-600 p-2"></textarea>
                      <p id="fb-error" class="text-red-600 text-sm hidden"></p>
                      <button id="send-event-feedback"
                              class="inline-flex items-center gap-2 px-5 py-2 rounded-full
                                     bg-indigo-600 text-white hover:bg-indigo-700
                                     shadow transition">
                        💾 Отправить отзыв
                      </button>
                    </div>
                `;
        const stars = document.querySelectorAll('#fb-stars span');
        const ratingInput = document.getElementById('fb-rating');

        function paint(upto) {
            stars.forEach(s => {
                const val = +s.dataset.value;
                if (val <= upto) {
                    s.textContent = '★';
                    s.classList.add('text-amber-400');
                    s.classList.remove('text-gray-400');
                } else {
                    s.textContent = '☆';
                    s.classList.remove('text-amber-400');
                    s.classList.add('text-gray-400');
                }
            });
        }

        stars.forEach(star => {
            star.addEventListener('mouseover', () => {
                paint(+star.dataset.value);
            });
            star.addEventListener('mouseout', () => {
                paint(+ratingInput.value || 0);
            });
            star.addEventListener('click', () => {
                const v = +star.dataset.value;
                ratingInput.value = v;
                paint(v);
            });
        });

        document.getElementById('send-event-feedback')
            .addEventListener('click', sendEventFeedback);
    });

    // Отправляем форму через AJAX и рендерим ответ
    function sendEventFeedback() {
        const rating = document.getElementById('fb-rating').value;
        const text = document.getElementById('fb-text').value.trim();
        const errEl = document.getElementById('fb-error');
        errEl.classList.add('hidden');

        if (!rating || !text) {
            errEl.textContent = 'Нужно указать и рейтинг, и текст.';
            errEl.classList.remove('hidden');
            return;
        }

        fetch("{% url 'leave_feedback_token' access_token=registration.access_token %}", {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'X-CSRFToken': csrftoken,
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: new URLSearchParams({rating, text})
        })
            .then(r => r.ok ? r.json() : r.json().then(e => Promise.reject(e)))
            .then(data => {
                // Заменяем секцию отзывов на «Спасибо» и ваш отзыв
                document.getElementById('event-feedback').innerHTML = `
                <p class="text-green-600 mb-4">✅ Спасибо за ваш отзыв!</p>
                <div class="bg-white dark:bg-[#262626] rounded-2xl shadow p-6">
                    <div class="mb-2 text-warning">
                        ${'★'.repeat(data.feedback.rating)}${'☆'.repeat(5 - data.feedback.rating)}
                    </div>
                    <p class="mb-2">${data.feedback.text}</p>
                    <small class="text-xs text-gray-500">
                        Оставлен ${new Date(data.feedback.created_at).toLocaleString('ru')}
                    </small>
                </div>
            `;
            })
            .catch(err => {
                errEl.textContent = err.message || 'Ошибка отправки';
                errEl.classList.remove('hidden');
            });
    }
});
