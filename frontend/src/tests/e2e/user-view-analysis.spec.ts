describe('MoodMarket Dashboard - Detailed Analysis View E2E Flow', () => {
  beforeEach(() => {
    cy.visit('/?ticker=AAPL');
  });

  it('allows a user to navigate through model explainability tabs', () => {
    // 1. Verify that Explainability Dashboard is rendered
    cy.contains('Model Diagnostics').should('exist');

    // 2. Click through SHAP Token Importance tab
    cy.contains('Token Importance').click();
    cy.contains('finbert').should('be.visible');

    // 3. Click through Attention Heatmap tab
    cy.contains('Attention weights').click();
    cy.get('canvas').should('exist'); // Heatmap charts

    // 4. Click through Prediction Breakdown tab
    cy.contains('Prediction Breakdown').click();
    cy.contains('Input Features').should('be.visible');
  });
});
