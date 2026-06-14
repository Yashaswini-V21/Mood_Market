describe('MoodMarket Dashboard - Search Ticker E2E Flow', () => {
  beforeEach(() => {
    cy.visit('/');
  });

  it('allows a user to search for a stock ticker and view live sentiment analysis', () => {
    // 1. Check title is visible
    cy.contains('MoodMarket').should('be.visible');

    // 2. Type ticker in search bar and submit
    cy.get('input[placeholder*="Search Ticker"]').first().type('AAPL');
    cy.get('form').first().submit();

    // 3. Verify page content updates to reflect the active stock AAPL
    cy.url().should('include', 'ticker=AAPL');
    
    // 4. Verify Sentiment Card and Trading Signal Cards exist
    cy.contains('Sentiment Analysis').should('exist');
    cy.contains('Trading Signal').should('exist');
  });
});
