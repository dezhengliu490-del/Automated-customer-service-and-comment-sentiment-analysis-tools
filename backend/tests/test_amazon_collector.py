from collector.amazon_collector import (
    _extract_asin,
    _extract_reviews,
    ParsedAmazonProduct,
)


def test_extract_asin_from_dp_url():
    assert _extract_asin("https://www.amazon.com/dp/B013KW38RQ") == "B013KW38RQ"


def test_extract_reviews_from_html():
    html = """
    <html>
      <body>
        <div data-hook="review" id="customer_review-1">
          <span class="a-profile-name">Jeff</span>
          <i data-hook="review-star-rating"><span>4.0 out of 5 stars</span></i>
          <a data-hook="review-title"><span>Great fit</span></a>
          <span data-hook="review-date">Reviewed in the United States on April 19, 2023</span>
          <span data-hook="review-body"><span>Comfortable and looks good.</span></span>
        </div>
      </body>
    </html>
    """
    product = ParsedAmazonProduct(
        asin="B013KW38RQ",
        domain="www.amazon.com",
        title="Legendary Whitetails Jacket",
        canonical_url="https://www.amazon.com/dp/B013KW38RQ",
        review_url="https://www.amazon.com/product-reviews/B013KW38RQ/",
    )
    rows = _extract_reviews(html, product)
    assert len(rows) == 1
    assert rows[0]["review_id"] == "customer_review-1"
    assert rows[0]["review_text"] == "Comfortable and looks good."
    assert rows[0]["reviewer_name"] == "Jeff"
    assert rows[0]["rating"] == "4.0"
    assert rows[0]["review_time"] == "2023-04-19"
