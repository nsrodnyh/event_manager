// CSRF
function getCookie(name) {
    const v = document.cookie.split('; ').find(r => r.startsWith(name + '='));
    return v ? decodeURIComponent(v.split('=')[1]) : '';
}

const csrftoken = getCookie('csrftoken');

document.addEventListener('DOMContentLoaded', () => {
    // Находим все кнопки «Оставить отзыв» для активностей
    document.querySelectorAll('.start-activity-feedback').forEach(btn => {
        btn.addEventListener('click', () => openActivityForm(btn));
    });

    function openActivityForm(btn) {
        const activityId = btn.dataset.activityId;
        const container = document.getElementById(`activity-feedback-${activityId}`);

        // Вставляем форму
        container.innerHTML = `
      <div id="fb-form-${activityId}"
           class="bg-white dark:bg-[#262626] rounded-2xl shadow p-6 space-y-4">
        <label class="block text-sm font-medium mb-1">Рейтинг</label>
        <div id="fb-stars-${activityId}"
             class="flex gap-1 text-3xl cursor-pointer select-none">
          ${[1, 2, 3, 4, 5].map(i =>
            `<span data-value="${i}"
                   class="text-gray-400 hover:text-amber-300">☆</span>`
        ).join('')}
        </div>
        <input type="hidden" id="fb-rating-${activityId}" value="">
        <label class="block text-sm font-medium">Комментарий</label>
        <textarea id="fb-text-${activityId}" rows="4"
                  class="w-full rounded-lg border-gray-300 dark:border-gray-600 p-2"></textarea>
        <p id="fb-error-${activityId}"
           class="text-red-600 text-sm hidden"></p>
        <button id="send-activity-feedback-${activityId}"
                class="inline-flex items-center gap-2 px-5 py-2 rounded-full
                       bg-indigo-600 text-white hover:bg-indigo-700
                       shadow transition">
          💾 Отправить отзыв
        </button>
      </div>
    `;

        // Логика заливки звёзд
        const stars = container.querySelectorAll(`#fb-stars-${activityId} span`);
        const ratingInput = container.querySelector(`#fb-rating-${activityId}`);

        function paint(upto) {
            stars.forEach(s => {
                const v = +s.dataset.value;
                if (v <= upto) {
                    s.textContent = '★';
                    s.classList.add('text-amber-400');
                    s.classList.remove('text-gray-400');
                } else {
                    s.textContent = '☆';
                    s.classList.add('text-gray-400');
                    s.classList.remove('text-amber-400');
                }
            });
        }

        stars.forEach(s => {
            s.addEventListener('mouseover', () => paint(+s.dataset.value));
            s.addEventListener('mouseout', () => paint(+ratingInput.value || 0));
            s.addEventListener('click', () => {
                const v = +s.dataset.value;
                ratingInput.value = v;
                paint(v);
            });
        });

        // Отправка формы
        container.querySelector(`#send-activity-feedback-${activityId}`)
            .addEventListener('click', () => sendActivityFeedback(activityId));
    }

    function sendActivityFeedback(activityId) {
        const textEl = document.getElementById(`fb-text-${activityId}`);
        const rating = document.getElementById(`fb-rating-${activityId}`).value;
        const text = textEl.value.trim();
        const errEl = document.getElementById(`fb-error-${activityId}`);
        errEl.classList.add('hidden');

        if (!rating || !text) {
            errEl.textContent = 'Нужно указать и рейтинг, и текст.';
            errEl.classList.remove('hidden');
            return;
        }

        // Собираем URL с заменой placeholder-а 0 на реальный activityId
        const url = "{% url 'leave_activity_feedback' access_token=registration.access_token activity_id=0 %}"
            .replace(/0$/, activityId);

        fetch(url, {
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
                // Рендерим «спасибо» + отзыв
                const starsHtml = Array.from({length: 5}, (_, i) =>
                    i < data.feedback.rating ? '★' : '☆'
                ).join('');
                const container = document.getElementById(`activity-feedback-${activityId}`);
                container.innerHTML = `
        <p class="text-green-600 mb-2">✅ Спасибо за ваш отзыв!</p>
        <div class="text-warning text-2xl mb-2">${starsHtml}</div>
        <p class="mb-2">${data.feedback.text}</p>
        <small class="text-xs text-gray-500">
          Оставлен ${new Date(data.feedback.created_at).toLocaleString('ru')}
        </small>
      `;
            })
            .catch(err => {
                errEl.textContent = err.message || 'Ошибка отправки';
                errEl.classList.remove('hidden');
            });
    }
});
