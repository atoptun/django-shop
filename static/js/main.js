document.addEventListener("DOMContentLoaded", function () {
  // Alerts
  const alerts = document.querySelectorAll(".messages-container .alert");

  alerts.forEach(function (alert) {
    setTimeout(function () {
      alert.style.transition = "transform 0.4s ease, opacity 0.4s ease";
      alert.style.opacity = "0";
      alert.style.transform = "translateX(50px)";

      setTimeout(() => alert.remove(), 400);
    }, 4000);

    alert.addEventListener("click", function () {
      alert.style.opacity = "0";
      setTimeout(() => alert.remove(), 200);
    });
  });

  function showAlertMessage(messageText, tags = "error") {
    const container = document.getElementById("messages-container");
    if (!container) return;

    const alertDiv = document.createElement("div");
    alertDiv.className = `alert alert-${tags}`;
    alertDiv.textContent = messageText;

    container.appendChild(alertDiv);

    setTimeout(() => {
      alertDiv.style.transition = "transform 0.4s ease, opacity 0.4s ease";
      alertDiv.style.opacity = "0";
      alertDiv.style.transform = "translateX(50px)";

      setTimeout(() => alertDiv.remove(), 400);
    }, 4000);
  }

  // Filter Logic (Keywords and Checkboxes)
  const form = document.getElementById("js-filter-form");
  const sortInput = document.getElementById("js-sort-input");

  document.querySelectorAll(".js-auto-submit").forEach((checkbox) => {
    checkbox.addEventListener("change", () => {
      htmx.trigger("#js-filter-form", "submit");
    });
  });

  const sortButtonsContainer = document.querySelector(".js-sort-buttons");
  if (sortButtonsContainer) {
    sortButtonsContainer.addEventListener("click", (e) => {
      const button = e.target.closest(".js-sort-button");
      if (sortInput && button && button.dataset.sortValue) {
        sortInput.value = button.dataset.sortValue;
        document
          .querySelectorAll(".js-sort-button")
          .forEach((btn) => btn.classList.remove("active-sort"));
        button.classList.add("active-sort");
        htmx.trigger("#js-filter-form", "submit");
      }
    });
  }

  function removeCategoryFilter(keyword) {
    const checkbox = document.querySelector(
      `.js-auto-submit[data-keyword="${keyword}"]`,
    );
    if (checkbox) {
      checkbox.checked = false;
      htmx.trigger("#js-filter-form", "submit");
    }
  }

  const keywordsList = document.querySelector(".js-keywords-list");
  const keywordsGroup = document.querySelectorAll(
    '.js-keywords-group input[type="checkbox"]',
  );

  if (keywordsList && keywordsGroup.length > 0) {
    keywordsGroup.forEach((checkbox) => {
      checkbox.addEventListener("change", function (e) {
        const keyword = this.dataset.keyword;
        if (this.checked) {
          if (
            !document.querySelector(
              `.js-keyword-tag[data-keyword="${keyword}"]`,
            )
          ) {
            const newTag = document.createElement("span");
            newTag.className = "keyword-tag js-keyword-tag";
            newTag.setAttribute("data-keyword", keyword);
            newTag.innerHTML = `${keyword} <i class="fa-solid fa-xmark remove-keyword-icon js-remove-keyword"></i>`;
            keywordsList.appendChild(newTag);
          }
        } else {
          const tagToRemove = document.querySelector(
            `.js-keyword-tag[data-keyword="${keyword}"]`,
          );
          if (tagToRemove) {
            tagToRemove.remove();
          }
        }
      });
    });

    keywordsList.addEventListener("click", function (event) {
      const keywordIcon = event.target.closest(".js-remove-keyword");
      if (keywordIcon) {
        const keywordTag = keywordIcon.closest(".js-keyword-tag");
        const keywordText = keywordTag.dataset.keyword;
        removeCategoryFilter(keywordText);
        keywordTag.remove();
      }
    });
  }

  // --- Logic for Product Detail Pages (product-*.html) ---
  const productPageContent = document.querySelector(".page-product");
  if (productPageContent) {
    // Accordion
    const accordionTitle = document.querySelector(".accordion-title");
    if (accordionTitle) {
      accordionTitle.addEventListener("click", function () {
        this.closest(".accordion-item").classList.toggle("active");
      });
    }
    // "Add to Cart" Button and Counter
    const cartControls = document.querySelector(".cart-controls");
    if (cartControls) {
      const productSlug = cartControls.dataset.productSlug;
      const addUrl = cartControls.dataset.addUrl;
      const updateUrl = cartControls.dataset.updateUrl;

      const addToCartForm = cartControls.querySelector("#add-to-cart-form");
      const quantityCounter = cartControls.querySelector("#quantity-counter");
      const decreaseBtn = quantityCounter.querySelector(
        '[data-action="decrease"]',
      );
      const increaseBtn = quantityCounter.querySelector(
        '[data-action="increase"]',
      );
      const quantityValueSpan =
        quantityCounter.querySelector(".quantity-value");

      const csrfToken = cartControls.querySelector(
        "[name=csrfmiddlewaretoken]",
      ).value;

      async function sendCartUpdate(url, actionValue) {
        const formData = new FormData();
        formData.append("action", actionValue);

        try {
          const response = await axios.post(url, formData, {
            headers: {
              "X-Requested-With": "XMLHttpRequest",
              "X-CSRFToken": csrfToken,
            },
          });
          const data = response.data;
          if (data.success) {
            updateView(data.product_quantity, data.cart_total_items);
          }
        } catch (error) {
          // if (error.response && error.response.data && error.response.data.error) {
          if (error?.response?.data?.error) {
            showAlertMessage(error.response.data.error, "error");
          } else {
            console.error("Cart update error:", error);
          }
        }
      }

      function updateView(qty, totalItems) {
        if (qty <= 0) {
          addToCartForm.classList.remove("is-hidden");
          quantityCounter.classList.add("is-hidden");
        } else {
          addToCartForm.classList.add("is-hidden");
          quantityCounter.classList.remove("is-hidden");
          quantityValueSpan.textContent = `${qty} in cart`;
        }

        // Update header count
        const headerCartBadge = document.querySelector(".js-cart-count");
        if (headerCartBadge) {
          headerCartBadge.textContent = totalItems;
        }
      }

      if (addToCartForm) {
        addToCartForm.addEventListener("submit", function (e) {
          e.preventDefault();
          sendCartUpdate(addUrl, "increase");
        });
      }

      decreaseBtn.addEventListener("click", function () {
        sendCartUpdate(updateUrl, "decrease");
      });

      increaseBtn.addEventListener("click", function () {
        sendCartUpdate(updateUrl, "increase");
      });
    }
  }

  // --- Logic for Cart Page (cart.html) ---
  const cartPageContent = document.querySelector(".cart-page-wrapper");
  if (cartPageContent) {
    const cartItemsList = document.getElementById("cart-items-list");
    const cartTotalPriceElem = document.getElementById("cart-total-price");

    if (cartItemsList) {
      cartItemsList.addEventListener("click", async function (event) {
        const btn = event.target.closest("button[type='submit']");
        if (!btn) return;
        event.preventDefault();

        const form = btn.closest("form");
        const cartItem = btn.closest(".cart-item");
        if (!form || !cartItem) return;

        const action = btn.value;
        const url = form.getAttribute("action");
        const csrfToken = form.querySelector(
          "[name=csrfmiddlewaretoken]",
        ).value;

        const formData = new FormData(form);
        if (action) {
          formData.append("action", action);
        }

        try {
          const response = await axios.post(url, formData, {
            headers: {
              "X-Requested-With": "XMLHttpRequest",
              "X-CSRFToken": csrfToken,
            },
          });

          const data = response.data;

          if (data.success) {
            const quantityElem = cartItem.querySelector(".quantity-value-cart");
            const itemTotalElem = cartItem.querySelector(
              "[data-item-total-price]",
            );

            if (data.product_quantity <= 0) {
              cartItem.remove();
              if (document.querySelectorAll(".cart-item").length === 0) {
                location.reload();
              }
            } else {
              if (quantityElem)
                quantityElem.textContent = data.product_quantity;
              if (itemTotalElem) itemTotalElem.textContent = data.item_subtotal;
            }

            if (cartTotalPriceElem)
              cartTotalPriceElem.textContent = data.cart_total_price;

            const headerCartBadge = document.querySelector(".js-cart-count");
            if (headerCartBadge)
              headerCartBadge.textContent = data.cart_total_items;
          }
        } catch (error) {
          // if (error.response && error.response.data && error.response.data.error) {
          if (error?.response?.data?.error) {
            showAlertMessage(error.response.data.error, "error");
          } else {
            console.error("Error updating cart:", error);
            form.submit();
          }
        }
      });
    }
  }

  // --- Logic for Account and Admin Pages ---
  const accountAdminWrapper = document.querySelector(
    ".account-page-wrapper, .admin-page-wrapper",
  );
  if (accountAdminWrapper) {
    // Account Page Tabs
    const accountTabs = document.querySelectorAll(".account-tab");
    const tabPanes = document.querySelectorAll(".tab-pane");
    if (accountTabs.length > 0 && tabPanes.length > 0) {
      accountTabs.forEach((tab) => {
        tab.addEventListener("click", function () {
          accountTabs.forEach((item) => item.classList.remove("active"));
          tabPanes.forEach((pane) => pane.classList.remove("active"));
          const targetPane = document.querySelector(this.dataset.tabTarget);
          this.classList.add("active");
          if (targetPane) targetPane.classList.add("active");
        });
      });
    }

    // Admin Panel - Category Tags
    const categoryTagsContainer = document.querySelector(".category-tags");
    if (categoryTagsContainer) {
      categoryTagsContainer.addEventListener("click", function (e) {
        const clickedTag = e.target.closest(".category-tag");
        if (clickedTag) {
          categoryTagsContainer
            .querySelectorAll(".category-tag")
            .forEach((t) => t.classList.remove("active"));
          clickedTag.classList.add("active");
        }
      });
    }

    // Image Upload Simulation
    const uploadButton = document.getElementById("upload-image-btn");
    const fileInput = document.getElementById("image-upload-input");

    if (uploadButton && fileInput) {
      uploadButton.addEventListener("click", function () {
        fileInput.click();
      });

      fileInput.addEventListener("change", function (event) {
        const file = event.target.files[0];
        if (file) {
          const reader = new FileReader();
          const placeholder = document.querySelector(
            ".image-upload-placeholder",
          );

          reader.onload = function (e) {
            placeholder.innerHTML = "";
            placeholder.style.backgroundImage = `url('${e.target.result}')`;
            placeholder.style.backgroundSize = "cover";
            placeholder.style.backgroundPosition = "center";
          };
          reader.readAsDataURL(file);
        }
      });
    }
  }
});
