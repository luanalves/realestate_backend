describe('Feature 016 - Property Mapping Fields UI', () => {
  const db = Cypress.env('ODOO_DB') || 'realestate'
  const username = Cypress.env('ODOO_USERNAME') || 'admin'
  const password = Cypress.env('ODOO_PASSWORD') || 'admin'

  const login = () => {
    cy.request({
      method: 'POST',
      url: '/web/session/authenticate',
      body: {
        jsonrpc: '2.0',
        method: 'call',
        params: {
          db,
          login: username,
          password,
        },
        id: Date.now(),
      },
    }).then((response) => {
      expect(response.status).to.eq(200)
      expect(response.body.result.uid).to.be.a('number')
    })
  }

  const rpc = (model, method, args = [], kwargs = {}) => (
    cy.request({
      method: 'POST',
      url: `/web/dataset/call_kw/${model}/${method}`,
      body: {
        jsonrpc: '2.0',
        method: 'call',
        params: { model, method, args, kwargs },
        id: Date.now(),
      },
    }).then((response) => {
      expect(response.status).to.eq(200)
      expect(response.body.error, JSON.stringify(response.body.error || {})).to.be.undefined
      return response.body.result
    })
  )

  const firstId = (model, domain = []) => (
    rpc(model, 'search_read', [domain], { fields: ['id'], limit: 1 })
      .then((records) => {
        expect(records, `${model} fixture`).to.have.length.greaterThan(0)
        return records[0].id
      })
  )

  const openPropertyForm = (propertyId) => {
    cy.visit(`/web#id=${propertyId}&action=quicksol_estate.action_property&model=real.estate.property&view_type=form`)
    cy.get('.o_form_view', { timeout: 20000 }).should('be.visible')
  }

  const clickTab = (label) => {
    cy.contains('.o_notebook .nav-link, .o_notebook_headers a', label, { timeout: 10000 })
      .scrollIntoView()
      .click({ force: true })
  }

  const assertMappedFieldsExist = (fields) => {
    fields.forEach(({ api, ui }) => {
      cy.log(`${api} -> ${ui}`)
      cy.get(`[name="${ui}"]`, { timeout: 10000 })
        .should('exist')
    })
  }

  const assertFieldContains = (field, expected) => {
    cy.get(`[name="${field}"]`, { timeout: 10000 }).should(($field) => {
      const text = $field.text().replace(/\s+/g, ' ').trim()
      const values = $field.find('input, textarea').toArray().map((input) => input.value).join(' ')
      const actual = `${text} ${values}`
      expect(actual.includes(expected) || actual.replace(/,/g, '').includes(expected), field).to.eq(true)
    })
  }

  const assertCheckbox = (field, checked = true) => {
    cy.get(`[name="${field}"] input[type="checkbox"]`, { timeout: 10000 })
      .should(checked ? 'be.checked' : 'not.be.checked')
  }

  const createFilledProperty = () => {
    const ts = Date.now()
    let propertyTypeId
    let locationTypeId
    let stateId
    let tagId
    let amenityId

    return firstId('real.estate.property.type')
      .then((id) => { propertyTypeId = id })
      .then(() => firstId('real.estate.location.type'))
      .then((id) => { locationTypeId = id })
      .then(() => firstId('res.country.state', [['country_id.code', '=', 'BR']]))
      .then((id) => { stateId = id })
      .then(() => rpc('real.estate.property.tag', 'create', [{ name: `US16 UI Tag ${ts}` }]))
      .then((id) => { tagId = id })
      .then(() => rpc('real.estate.amenity', 'create', [{ name: `US16 UI Amenity ${ts}` }]))
      .then((id) => { amenityId = id })
      .then(() => rpc('real.estate.property', 'create', [{
        name: `US16 UI Filled Property ${ts}`,
        property_type_id: propertyTypeId,
        property_purpose: 'residential',
        origin_media: 'website',
        activity_notification: 'all',
        send_activities_to_owner: true,
        owner_email: `owner.ui.${ts}@example.com`,
        owner_home_phone: '(11) 3333-4444',
        owner_business_phone: '(11) 2222-3333',
        owner_mobile_phone: '(11) 98888-7777',
        phone_ids: [[0, 0, {
          phone: '(11) 98888-7777',
          phone_type: 'mobile',
          notes: 'US16 UI phone note',
        }]],
        email_ids: [[0, 0, {
          email: `contact.ui.${ts}@example.com`,
          email_type: 'work',
          notes: 'US16 UI email note',
        }]],
        floor_number: 8,
        unit_number: '81B',
        num_floors: 18,
        construction_year: 2012,
        reform_year: 2020,
        registered_by: 'UI Cypress',
        alternative_reference: `UI-ALT-${ts}`,
        zip_code: '01310-100',
        state_id: stateId,
        city: 'Sao Paulo',
        neighborhood: 'Bela Vista',
        street: 'Rua API Mapping',
        street_number: '100',
        complement: 'Suite 12',
        location_type_id: locationTypeId,
        for_sale: true,
        price: 850000,
        for_rent: true,
        rent_price: 4200,
        iptu_annual: 3600,
        iptu_payment_condition: 'annual',
        iptu_value: '1200.00',
        insurance_value: 980,
        rental_guarantee_insurance: 'required',
        fire_insurance: 'included',
        condominium_fee: 750,
        property_status: 'available',
        condition: 'excellent',
        status: 'available',
        property_situation: 'Desocupado',
        intention: 'sale',
        exclusivity: true,
        authorization_start_date: '2026-01-15',
        authorization_end_date: '2026-12-15',
        accepts_fgts: true,
        accepts_financing: true,
        used_fgts: true,
        fgts_last_usage_date: '2024-03-10',
        fgts_usage_notes: 'Uso identificado na matricula anterior',
        area: 120,
        total_area: 250,
        private_area: 180,
        land_area: 320,
        num_rooms: 4,
        num_suites: 1,
        num_bathrooms: 3,
        num_parking: 2,
        amenities: [[6, 0, [amenityId]]],
        zoning_type: 'residential',
        zoning_restrictions: 'US16 zoning restriction note',
        tag_ids: [[6, 0, [tagId]]],
        key_location: 'front desk',
        key_ids: [[0, 0, {
          key_code: `KEY-${ts}`,
          key_type: 'original',
          quantity: 2,
          status: 'available',
          location: 'front desk',
          notes: 'US16 key note',
        }]],
        publish_website: true,
        publish_featured: true,
        publish_super_featured: false,
        youtube_video_url: 'https://youtube.com/watch?v=abc123',
        virtual_tour_url: 'https://example.com/tour',
        meta_title: 'US16 Meta Title',
        meta_description: 'US16 meta description',
        meta_keywords: 'us16,property,mapping',
        description_short: 'US16 short description',
        description: '<p>US16 complete property description</p>',
        internal_notes: 'internal api note',
        has_sign: true,
        sign_type: 'sale',
        sign_installation_date: '2026-02-01',
        sign_removal_date: '2026-11-30',
        sign_notes: 'US16 sign note',
        commission_type: 'percentage',
        captured_intention: 'sale',
        included_in_commission_date: '2026-05-04',
        commercial_condition: 'Condição comercial padrão',
        matricula_number: `REG-${ts}`,
        iptu_code: `IPTU-${ts}`,
        electricity_network_code: `ELEC-${ts}`,
        water_network_code: `WATER-${ts}`,
        titles_rights: 'ok',
        approved_environmental_agency: true,
        approved_project: true,
        documentation_observations: 'docs ok',
      }]))
  }

  beforeEach(() => {
    login()
  })

  it('shows filled Feature 016 mapping fields in the Odoo property form tabs', () => {
    createFilledProperty().then((propertyId) => {
      openPropertyForm(propertyId)
    })

    clickTab('Dados do Proprietário')
    assertMappedFieldsExist([
      { api: 'source_medium', ui: 'origin_media' },
      { api: 'send_activities_to_owner', ui: 'send_activities_to_owner' },
      { api: 'owner_email', ui: 'owner_email' },
      { api: 'owner_home_phone', ui: 'owner_home_phone' },
      { api: 'owner_business_phone', ui: 'owner_business_phone' },
      { api: 'owner_mobile_phone', ui: 'owner_mobile_phone' },
    ])
    assertFieldContains('owner_email', 'owner.ui.')
    assertFieldContains('owner_home_phone', '(11) 3333-4444')
    assertFieldContains('owner_business_phone', '(11) 2222-3333')
    assertFieldContains('owner_mobile_phone', '(11) 98888-7777')
    assertCheckbox('send_activities_to_owner')
    cy.contains('US16 UI phone note', { timeout: 10000 }).should('exist')
    cy.contains('US16 UI email note', { timeout: 10000 }).should('exist')

    clickTab('Structure')
    assertMappedFieldsExist([
      { api: 'registered_by', ui: 'registered_by' },
      { api: 'alternative_reference', ui: 'alternative_reference' },
      { api: 'year_of_renovation', ui: 'reform_year' },
    ])
    assertFieldContains('registered_by', 'UI Cypress')
    assertFieldContains('alternative_reference', 'UI-ALT-')
    assertFieldContains('floor_number', '8')
    assertFieldContains('unit_number', '81B')
    assertFieldContains('num_floors', '18')
    assertFieldContains('construction_year', '2012')
    assertFieldContains('reform_year', '2020')

    clickTab('Location')
    assertMappedFieldsExist([
      { api: 'search_street', ui: 'street' },
    ])
    assertFieldContains('street', 'Rua API Mapping')
    assertFieldContains('neighborhood', 'Bela Vista')
    assertFieldContains('complement', 'Suite 12')

    clickTab('Primary Data')
    assertMappedFieldsExist([
      { api: 'iptu_payment_condition', ui: 'iptu_payment_condition' },
      { api: 'iptu_value', ui: 'iptu_value' },
      { api: 'rental_guarantee_insurance', ui: 'rental_guarantee_insurance' },
      { api: 'fire_insurance', ui: 'fire_insurance' },
      { api: 'property_situation', ui: 'property_situation' },
      { api: 'intention', ui: 'intention' },
      { api: 'exclusivity', ui: 'exclusivity' },
    ])
    assertFieldContains('iptu_payment_condition', 'annual')
    assertFieldContains('iptu_value', '1200.00')
    assertFieldContains('rental_guarantee_insurance', 'required')
    assertFieldContains('fire_insurance', 'included')
    assertFieldContains('property_situation', 'Desocupado')
    assertFieldContains('intention', 'sale')
    assertFieldContains('authorization_start_date', '01/15/2026')
    assertFieldContains('authorization_end_date', '12/15/2026')
    assertCheckbox('exclusivity')
    assertCheckbox('accepts_fgts')
    assertCheckbox('accepts_financing')
    assertCheckbox('used_fgts')
    assertFieldContains('fgts_last_usage_date', '03/10/2024')
    assertFieldContains('fgts_eligible_from', '03/11/2027')
    assertCheckbox('fgts_eligible_now', false)
    assertFieldContains('fgts_usage_notes', 'Uso identificado na matricula anterior')

    clickTab('Features')
    assertFieldContains('total_area', '250.00')
    assertFieldContains('private_area', '180.00')
    assertFieldContains('land_area', '320.00')
    assertFieldContains('num_rooms', '4')
    assertFieldContains('num_suites', '1')
    assertFieldContains('num_bathrooms', '3')
    assertFieldContains('num_parking', '2')
    cy.contains('US16 UI Amenity', { timeout: 10000 }).should('be.visible')

    clickTab('Zoning')
    assertMappedFieldsExist([
      { api: 'zoning', ui: 'zoning_type' },
    ])
    assertFieldContains('zoning_type', 'Residential')
    assertFieldContains('zoning_restrictions', 'US16 zoning restriction note')

    clickTab('Tags')
    assertMappedFieldsExist([
      { api: 'tags', ui: 'tag_ids' },
    ])
    cy.contains('US16 UI Tag', { timeout: 10000 }).should('be.visible')

    clickTab('Key Control')
    assertMappedFieldsExist([
      { api: 'key_location', ui: 'key_location' },
    ])
    assertFieldContains('key_location', 'front desk')
    cy.contains('US16 key note', { timeout: 10000 }).should('exist')

    clickTab('Web Publishing')
    assertMappedFieldsExist([
      { api: 'advertise', ui: 'publish_website' },
      { api: 'virtual_tour', ui: 'virtual_tour_url' },
      { api: 'youtube_video', ui: 'youtube_video_url' },
      { api: 'internal_comments', ui: 'internal_notes' },
    ])
    assertMappedFieldsExist([
      { api: 'featured_property', ui: 'publish_featured' },
      { api: 'super_featured', ui: 'publish_super_featured' },
    ])
    assertCheckbox('publish_website')
    assertCheckbox('publish_featured')
    assertCheckbox('publish_super_featured', false)
    assertFieldContains('virtual_tour_url', 'https://example.com/tour')
    assertFieldContains('youtube_video_url', 'https://youtube.com/watch?v=abc123')
    assertFieldContains('meta_title', 'US16 Meta Title')
    assertFieldContains('meta_description', 'US16 meta description')
    assertFieldContains('meta_keywords', 'us16,property,mapping')
    assertFieldContains('description_short', 'US16 short description')
    cy.contains('US16 complete property description', { timeout: 10000 }).should('exist')
    assertFieldContains('internal_notes', 'internal api note')

    clickTab('Signs')
    assertMappedFieldsExist([
      { api: 'sign_on_site', ui: 'has_sign' },
      { api: 'super_featured', ui: 'publish_super_featured' },
    ])
    assertCheckbox('has_sign')
    assertFieldContains('sign_type', 'For Sale')
    assertFieldContains('sign_installation_date', '02/01/2026')
    assertFieldContains('sign_removal_date', '11/30/2026')
    assertFieldContains('sign_notes', 'US16 sign note')

    clickTab('Commissions')
    assertMappedFieldsExist([
      { api: 'commission_type', ui: 'commission_type' },
      { api: 'captured_intention', ui: 'captured_intention' },
      { api: 'included_in_commission_date', ui: 'included_in_commission_date' },
      { api: 'commercial_condition', ui: 'commercial_condition' },
    ])
    assertFieldContains('commission_type', 'percentage')
    assertFieldContains('captured_intention', 'sale')
    assertFieldContains('included_in_commission_date', '05/04/2026')
    assertFieldContains('commercial_condition', 'Condição comercial padrão')

    clickTab('Documents')
    assertMappedFieldsExist([
      { api: 'registration_number', ui: 'matricula_number' },
      { api: 'iptu_code', ui: 'iptu_code' },
      { api: 'electricity_network_code', ui: 'electricity_network_code' },
      { api: 'water_network_code', ui: 'water_network_code' },
      { api: 'titles_rights', ui: 'titles_rights' },
      { api: 'approved_environmental_agency', ui: 'approved_environmental_agency' },
      { api: 'approved_project', ui: 'approved_project' },
      { api: 'documentation_observations', ui: 'documentation_observations' },
      { api: 'property_files', ui: 'document_ids' },
    ])
    assertFieldContains('matricula_number', 'REG-')
    assertFieldContains('iptu_code', 'IPTU-')
    assertFieldContains('electricity_network_code', 'ELEC-')
    assertFieldContains('water_network_code', 'WATER-')
    assertFieldContains('titles_rights', 'ok')
    assertCheckbox('approved_environmental_agency')
    assertCheckbox('approved_project')
    assertFieldContains('documentation_observations', 'docs ok')
  })
})
