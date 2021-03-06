<?php

class LocationSearchTest extends TestCase
{
    private function checkLocationSearchTableContent($content)
    {
        $requiredSubstrings = ['Location Search Results', 'Radius'];
        foreach ($requiredSubstrings as $requiredSubstring) {
            $this->assertTrue(strpos($content, $requiredSubstring) !== false);
        }
    }
    
    public function testUngroupedLocations()
    {
        $response = $this->get('/location/search?location_group_id=0&view=table');
        $this->assertEquals(200, $response->getStatusCode());
        $content = $response->getContent();
        $this->assertTrue(strpos($content, 'spreadsheet') !== false);
        $this->checkLocationSearchTableContent($content);
    }
    
    public function testUntaggedLocations()
    {
        $response = $this->get('/location/search?location_tag_id=0&view=table');
        $this->assertEquals(200, $response->getStatusCode());
        $content = $response->getContent();
        $this->assertTrue(strpos($content, 'spreadsheet') !== false);
        $this->checkLocationSearchTableContent($content);
    }

    public function testSortByName()
    {
        $response = $this->get('/location/search?location_tag_id=1&keywords=&order_by=name&view=table');
        $this->assertEquals(200, $response->getStatusCode());
        $content = $response->getContent();
        $this->assertTrue(strpos($content, 'spreadsheet sort-by-name') !== false);
        $this->checkLocationSearchTableContent($content);
    }

    public function testSortByDistance()
    {
        $response = $this->get('/location/search?location_tag_id=1&keywords=&order_by=distance&view=table');
        $this->assertEquals(200, $response->getStatusCode());
        $content = $response->getContent();
        $this->assertTrue(strpos($content, 'spreadsheet sort-by-distance') !== false);
        $this->checkLocationSearchTableContent($content);
    }

    public function testSortByRating()
    {
        $response = $this->get('/location/search?location_tag_id=1&keywords=&order_by=rating&view=table');
        $this->assertEquals(200, $response->getStatusCode());
        $content = $response->getContent();
        $this->assertTrue(strpos($content, 'spreadsheet sort-by-rating') !== false);
        $this->checkLocationSearchTableContent($content);
    }

    public function testMapView()
    {
        $response = $this->get('/location/search?keywords=&order_by=rating&location_tag_id=1&view=map');
        $this->assertEquals(200, $response->getStatusCode());
        $content = $response->getContent();
        $this->assertTrue(strpos($content, 'Location Search Results') !== false);
        $this->assertTrue(strpos($content, ' id="map"') !== false);
    }
}
